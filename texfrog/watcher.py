"""File watcher for TeXFrog live-reload.

Monitors proof source files for changes and triggers safe rebuilds.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import threading
import time
from pathlib import Path

import yaml
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


def collect_watched_files(yaml_path: Path) -> set[Path]:
    """Return the set of absolute paths that should be monitored.

    Reads the YAML file to discover the source, macros, and preamble
    paths.  All paths are resolved relative to the YAML file's parent
    directory.

    Args:
        yaml_path: Absolute path to the proof YAML config file.

    Returns:
        A set of resolved absolute paths including the YAML file itself,
        the source .tex file, all macro files, and the preamble file
        (if specified).
    """
    paths: set[Path] = {yaml_path}
    base_dir = yaml_path.parent

    try:
        with yaml_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception:
        return paths

    if not isinstance(data, dict):
        return paths

    source_rel = data.get("source")
    if source_rel:
        paths.add((base_dir / source_rel).resolve())

    for macro_rel in data.get("macros", []):
        paths.add((base_dir / macro_rel).resolve())

    preamble_rel = data.get("preamble")
    if preamble_rel:
        paths.add((base_dir / preamble_rel).resolve())

    return paths


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
    yaml_path: Path,
    output_dir: Path,
    keep_tmp: bool,
) -> bool:
    """Parse the proof and rebuild the HTML site safely.

    On success the *output_dir* is updated with new content.  On failure
    the existing *output_dir* is left untouched and the error is logged.

    Returns:
        ``True`` if the rebuild succeeded, ``False`` otherwise.
    """
    from .parser import parse_proof
    from .output.html import generate_html

    logger.info("Rebuilding …")
    start = time.monotonic()

    try:
        proof = parse_proof(yaml_path)
    except Exception as exc:
        logger.error("Parse error (keeping existing site): %s", exc)
        return False

    staging_dir = Path(tempfile.mkdtemp(
        prefix="texfrog_live_", dir=output_dir.parent,
    ))
    try:
        generate_html(proof, yaml_path.parent, staging_dir, keep_tmp=keep_tmp)
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
    yaml_path: Path,
    output_dir: Path,
    keep_tmp: bool,
    version: list[int],
    debounce_seconds: float = 0.5,
) -> Observer:
    """Start watching proof source files for changes.

    Args:
        yaml_path: Absolute path to the proof YAML config.
        output_dir: Destination directory for the HTML site.
        keep_tmp: Whether to preserve intermediate files.
        version: A mutable ``[int]`` list.  ``version[0]`` is incremented
            after each successful rebuild so the browser can detect changes.
        debounce_seconds: Quiet period before triggering rebuild.

    Returns:
        The running watchdog ``Observer`` instance.
    """
    watched = collect_watched_files(yaml_path)
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
            current_watched = collect_watched_files(yaml_path)
            current_mtimes = _snapshot_mtimes(current_watched)
            if current_mtimes == last_mtimes:
                logger.info("No file changes detected, skipping rebuild.")
                return

            success = safe_rebuild(yaml_path, output_dir, keep_tmp)
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
