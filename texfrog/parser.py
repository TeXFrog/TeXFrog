"""Parse TeXFrog YAML input files and combined tagged LaTeX source."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

from .model import Figure, Game, Proof, SourceLine
from .packages import get_profile

# Matches a %:tags: comment at the end of a line.
# Captures the tag string, e.g. "G1,G3-G5".
_TAG_RE = re.compile(r"\s*%:tags:\s*(.+?)\s*$")

# Labels must contain only alphanumeric characters, underscores, and hyphens.
# This prevents path traversal when labels are used as filenames.
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_-]+$")


def resolve_tag_ranges(tag_string: str, ordered_labels: list[str]) -> frozenset[str]:
    """Convert a tag string like "G0,G3-G5" to a frozenset of labels.

    Ranges are resolved by position in ``ordered_labels``.  A range
    "A-B" includes every label from A to B inclusive (in list order).
    Single labels outside the ordered list are still accepted verbatim
    (they simply never match any game and are therefore silently ignored
    at filtering time — useful for future-proofing or typos that the
    user catches separately).

    Args:
        tag_string: Comma-separated tokens, each either a single label
            or a "start-end" range.
        ordered_labels: The full ordered list of game/reduction labels
            from the proof config.

    Returns:
        A frozenset of resolved label strings.

    Raises:
        ValueError: If a range endpoint is not found in ordered_labels.
    """
    label_index = {label: i for i, label in enumerate(ordered_labels)}
    result: set[str] = set()

    for token in tag_string.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            # Could be a range like "G3-G5" or a single label containing "-"
            # Strategy: try splitting on the first "-" that gives two valid labels.
            # If no such split exists, treat the whole token as a single label.
            parts = token.split("-")
            resolved = False
            for split_at in range(1, len(parts)):
                start = "-".join(parts[:split_at])
                end = "-".join(parts[split_at:])
                if start in label_index and end in label_index:
                    i_start = label_index[start]
                    i_end = label_index[end]
                    if i_start > i_end:
                        raise ValueError(
                            f"Range '{token}' is reversed: '{start}' comes after '{end}' "
                            f"in the game order."
                        )
                    result.update(ordered_labels[i_start : i_end + 1])
                    resolved = True
                    break
            if not resolved:
                # Treat as a literal label (may not exist in ordered_labels)
                result.add(token)
        else:
            result.add(token)

    return frozenset(result)


def parse_source_line(raw_line: str, ordered_labels: list[str]) -> SourceLine:
    """Parse a single raw line from the combined source file.

    Strips a ``%:tags:`` comment if present and resolves the tag string
    to a frozenset of game labels.  Returns a :class:`SourceLine` with
    ``tags=None`` if there is no tag comment (line appears in all games).

    Args:
        raw_line: A single line from the source file (with trailing newline
            already stripped by the caller).
        ordered_labels: Ordered game labels for range resolution.

    Returns:
        A :class:`SourceLine` instance.
    """
    match = _TAG_RE.search(raw_line)
    if match:
        tag_str = match.group(1)
        content = raw_line[: match.start()]
        tags: Optional[frozenset[str]] = resolve_tag_ranges(tag_str, ordered_labels)
    else:
        content = raw_line
        tags = None
    return SourceLine(content=content, tags=tags, original=raw_line)


def parse_source_file(path: Path, ordered_labels: list[str]) -> list[SourceLine]:
    """Parse the combined tagged LaTeX source file.

    Args:
        path: Path to the combined source ``.tex`` file.
        ordered_labels: Ordered game labels for range resolution.

    Returns:
        List of :class:`SourceLine` objects, one per physical line.
    """
    lines: list[SourceLine] = []
    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            lines.append(parse_source_line(raw_line.rstrip("\n"), ordered_labels))
    return lines


def parse_proof(yaml_path: Path) -> Proof:
    """Parse a TeXFrog YAML proof config file.

    The YAML file format is documented in the project README.  Key fields:

    * ``macros`` — list of macro file paths (relative to the YAML file)
    * ``source`` — path to the combined tagged source ``.tex`` file
    * ``games`` — ordered list of ``{label, latex_name, description}`` dicts
    * ``commentary`` — mapping from game label to LaTeX commentary text (optional)
    * ``figures`` — list of ``{label, games}`` dicts for consolidated figures (optional)

    Args:
        yaml_path: Path to the ``.yaml`` proof config file.

    Returns:
        A fully populated :class:`Proof` instance.

    Raises:
        FileNotFoundError: If the source file does not exist.
        ValueError: If required fields are missing.
    """
    yaml_path = Path(yaml_path).resolve()
    base_dir = yaml_path.parent

    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    # --- package ---
    package_name: str = data.get("package", "cryptocode")
    get_profile(package_name)  # validate early; raises ValueError if unknown

    # --- preamble ---
    preamble_rel: str | None = data.get("preamble")
    if preamble_rel:
        preamble_path = (base_dir / preamble_rel).resolve()
        if not preamble_path.is_relative_to(base_dir):
            raise ValueError(
                f"Preamble path '{preamble_rel}' resolves outside the proof directory."
            )
        if not preamble_path.exists():
            raise FileNotFoundError(f"Preamble file not found: {preamble_path}")

    # --- macros ---
    macros: list[str] = data.get("macros", [])
    for macro_rel in macros:
        macro_path = (base_dir / macro_rel).resolve()
        if not macro_path.is_relative_to(base_dir):
            raise ValueError(
                f"Macro path '{macro_rel}' resolves outside the proof directory."
            )

    # --- games ---
    raw_games = data.get("games", [])
    if not raw_games:
        raise ValueError("'games' list is required and must not be empty.")
    games: list[Game] = []
    for entry in raw_games:
        label = entry["label"]
        if not _SAFE_LABEL.match(label):
            raise ValueError(
                f"Game label '{label}' contains unsafe characters. "
                f"Labels must match [A-Za-z0-9_-]."
            )
        games.append(
            Game(
                label=label,
                latex_name=entry["latex_name"],
                description=entry["description"],
                reduction=bool(entry.get("reduction", False)),
                related_games=list(entry.get("related_games", [])),
            )
        )
    ordered_labels = [g.label for g in games]

    # Validate related_games
    for game in games:
        if game.related_games:
            if not game.reduction:
                raise ValueError(
                    f"Game '{game.label}' has related_games but is not a reduction. "
                    f"related_games is only valid on entries with reduction: true."
                )
            if len(game.related_games) > 2:
                raise ValueError(
                    f"Reduction '{game.label}' has {len(game.related_games)} related_games "
                    f"(maximum is 2)."
                )
            for ref_label in game.related_games:
                if ref_label not in ordered_labels:
                    raise ValueError(
                        f"Reduction '{game.label}' references unknown related game "
                        f"'{ref_label}'. Available labels: {ordered_labels}"
                    )

    # --- source ---
    source_rel = data.get("source")
    if not source_rel:
        raise ValueError("'source' field (path to combined .tex file) is required.")
    source_path = (base_dir / source_rel).resolve()
    if not source_path.is_relative_to(base_dir):
        raise ValueError(
            f"Source path '{source_rel}' resolves outside the proof directory."
        )
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    source_lines = parse_source_file(source_path, ordered_labels)

    # --- commentary ---
    commentary: dict[str, str] = data.get("commentary") or {}

    # --- figures ---
    raw_figures = data.get("figures") or []
    figures: list[Figure] = []
    for entry in raw_figures:
        label = entry["label"]
        if not _SAFE_LABEL.match(label):
            raise ValueError(
                f"Figure label '{label}' contains unsafe characters. "
                f"Labels must match [A-Za-z0-9_-]."
            )
        games_str = entry["games"]
        resolved = list(resolve_tag_ranges(games_str, ordered_labels))
        # Preserve the order from ordered_labels for deterministic output
        ordered_figure_games = [l for l in ordered_labels if l in resolved]
        figures.append(Figure(
            label=label,
            games=ordered_figure_games,
            procedure_name=entry.get("procedure_name"),
        ))

    return Proof(
        macros=macros,
        games=games,
        source_lines=source_lines,
        commentary=commentary,
        figures=figures,
        package=package_name,
        preamble=preamble_rel,
    )
