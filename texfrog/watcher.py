"""File watcher for TeXFrog live-reload.

Monitors proof source files for changes and triggers safe rebuilds.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


def _snapshot_mtimes(files: set[Path]) -> dict[Path, float]:
    """Return a dict mapping each path to its current mtime.

    Files that do not exist (or cannot be stat'd) are omitted.
    """
    result: dict[Path, float] = {}
    for p in files:
        try:
            result[p] = p.stat().st_mtime
        except OSError:
            pass
    return result


def _collect_watched_files_tex(tex_path: Path) -> set[Path]:
    """Collect watched files from a .tex proof file."""
    paths: set[Path] = {tex_path}
    base_dir = tex_path.parent

    try:
        text = tex_path.read_text(encoding="utf-8")
    except Exception:
        return paths

    for m in re.finditer(r"\\tfmacrofile\{([^}]+)\}", text):
        paths.add((base_dir / m.group(1).strip()).resolve())

    for m in re.finditer(r"\\tfpreamble\{([^}]+)\}", text):
        paths.add((base_dir / m.group(1).strip()).resolve())

    for m in re.finditer(r"\\tfcommentary\{[^}]+\}\{[^}]+\}\{([^}]+)\}", text):
        paths.add((base_dir / m.group(1).strip()).resolve())

    for m in re.finditer(r"\\input\{([^}]+)\}", text):
        paths.add((base_dir / m.group(1).strip()).resolve())

    return paths


def collect_watched_files(input_path: Path) -> set[Path]:
    """Return the set of absolute paths that should be monitored.

    Args:
        input_path: Absolute path to the proof .tex file.

    Returns:
        A set of resolved absolute paths including the input file itself
        and all referenced source/macro/commentary files.
    """
    return _collect_watched_files_tex(input_path)


class _DebouncedHandler(FileSystemEventHandler):
    """Watchdog event handler that debounces rapid file changes.

    Accumulates file-change events and calls a callback after a quiet
    period (no new events for *debounce_seconds*).
    """

    def __init__(
        self,
        watched_files: set[Path],
        on_change: callable,
        debounce_seconds: float = 0.5,
    ) -> None:
        super().__init__()
        self._watched_files = watched_files
        self._on_change = on_change
        self._debounce_seconds = debounce_seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def update_watched_files(self, new_files: set[Path]) -> None:
        """Replace the set of watched files (thread-safe)."""
        with self._lock:
            self._watched_files = new_files

    def cancel_pending(self) -> None:
        """Cancel any pending debounce timer (thread-safe)."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        event_path = Path(event.src_path).resolve()
        with self._lock:
            if event_path not in self._watched_files:
                return
        self._reset_timer()

    def _reset_timer(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_seconds, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        logger.info("Change detected, triggering rebuild …")
        try:
            self._on_change()
        except Exception:
            logger.exception("Error in rebuild callback")


def safe_rebuild(
    input_path: Path,
    output_dir: Path,
    keep_tmp: bool,
) -> bool:
    """Parse the proof and rebuild the HTML site safely.

    On success the *output_dir* is updated with new content.  On failure
    the existing *output_dir* is left untouched and the error is logged.

    Returns:
        ``True`` if the rebuild succeeded, ``False`` otherwise.
    """
    from .output.html import generate_html, generate_index_page
    from .tex_parser import parse_tex_proofs
    from .validate import validate_proof

    logger.info("Rebuilding …")
    start = time.monotonic()

    try:
        proofs = parse_tex_proofs(input_path)
        for proof in proofs:
            for msg in validate_proof(proof, input_path.parent):
                logger.warning(msg)
    except Exception as exc:
        logger.error("Parse error (keeping existing site): %s", exc)
        return False

    staging_dir = Path(tempfile.mkdtemp(
        prefix="texfrog_live_", dir=output_dir.parent,
    ))
    try:
        if len(proofs) == 1:
            generate_html(proofs[0], input_path.parent, staging_dir, keep_tmp=keep_tmp)
        else:
            for proof in proofs:
                proof_out = staging_dir / proof.source_name
                generate_html(proof, input_path.parent, proof_out, keep_tmp=keep_tmp)
            generate_index_page(proofs, staging_dir)
    except Exception as exc:
        logger.error("Build error (keeping existing site): %s", exc)
        shutil.rmtree(staging_dir, ignore_errors=True)
        return False

    old_dir = output_dir.with_name(output_dir.name + ".old")
    try:
        if old_dir.exists():
            shutil.rmtree(old_dir)
        if output_dir.exists():
            output_dir.rename(old_dir)
        staging_dir.rename(output_dir)
        if old_dir.exists():
            shutil.rmtree(old_dir, ignore_errors=True)
    except OSError as exc:
        logger.error("Failed to swap build output: %s", exc)
        if old_dir.exists() and not output_dir.exists():
            old_dir.rename(output_dir)
        shutil.rmtree(staging_dir, ignore_errors=True)
        return False

    elapsed = time.monotonic() - start
    logger.info("Rebuild succeeded in %.1fs", elapsed)
    return True


def start_watcher(
    input_path: Path,
    output_dir: Path,
    keep_tmp: bool,
    version: list[int],
    debounce_seconds: float = 0.5,
) -> Observer:
    """Start watching proof source files for changes.

    Args:
        input_path: Absolute path to the proof .tex file.
        output_dir: Destination directory for the HTML site.
        keep_tmp: Whether to preserve intermediate files.
        version: A mutable ``[int]`` list.  ``version[0]`` is incremented
            after each successful rebuild so the browser can detect changes.
        debounce_seconds: Quiet period before triggering rebuild.

    Returns:
        The running watchdog ``Observer`` instance.
    """
    watched = collect_watched_files(input_path)
    watched_dirs = {p.parent for p in watched}
    rebuild_lock = threading.Lock()
    last_mtimes = _snapshot_mtimes(watched)

    def on_change() -> None:
        nonlocal last_mtimes
        if not rebuild_lock.acquire(blocking=False):
            logger.info("Rebuild already in progress, skipping.")
            return
        try:
            # Check whether any file has actually changed since the last
            # successful build.  macOS FSEvents can deliver duplicate
            # events well after the debounce window, so we must guard
            # against redundant rebuilds of unchanged content.
            current_watched = collect_watched_files(input_path)
            current_mtimes = _snapshot_mtimes(current_watched)
            if current_mtimes == last_mtimes:
                logger.info("No file changes detected, skipping rebuild.")
                return

            success = safe_rebuild(input_path, output_dir, keep_tmp)
            if success:
                version[0] += 1
                logger.info("Version bumped to %d", version[0])
                last_mtimes = _snapshot_mtimes(current_watched)
                handler.update_watched_files(current_watched)
                new_dirs = {p.parent for p in current_watched}
                for d in new_dirs - on_change._dirs:
                    observer.schedule(handler, str(d), recursive=False)
                    logger.info("Now watching new directory: %s", d)
                on_change._dirs = new_dirs
        finally:
            # Discard any events that arrived during the rebuild so they
            # don't trigger a redundant second rebuild of unchanged files.
            handler.cancel_pending()
            rebuild_lock.release()

    on_change._dirs = watched_dirs

    handler = _DebouncedHandler(watched, on_change, debounce_seconds)
    observer = Observer()
    for d in watched_dirs:
        observer.schedule(handler, str(d), recursive=False)
    observer.daemon = True
    observer.start()

    watched_names = sorted(p.name for p in watched)
    logger.info("Watching %d file(s): %s", len(watched), ", ".join(watched_names))
    return observer
