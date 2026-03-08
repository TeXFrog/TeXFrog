"""Parse TeXFrog commands from .tex files.

Extracts game definitions, source content, and metadata from a LaTeX file
that uses the texfrog.sty package.  This replaces the YAML parser for the
Python HTML export pipeline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .model import Figure, Game, Proof, SourceLine
from .packages import get_profile
from .parser import resolve_tag_ranges


# -----------------------------------------------------------------------
# Brace-matching helpers
# -----------------------------------------------------------------------

def find_brace_group(text: str, pos: int) -> tuple[str, int]:
    """Find a brace-delimited group ``{...}`` starting at *pos*.

    Args:
        text: The full text.
        pos: Index of the opening ``{``.

    Returns:
        ``(content, end)`` where *content* is everything between the
        braces (excluding them) and *end* is the index just past the
        closing ``}``.

    Raises:
        ValueError: If *pos* doesn't point to ``{`` or braces are unbalanced.
    """
    if pos >= len(text) or text[pos] != "{":
        raise ValueError(f"Expected '{{' at position {pos}")
    depth = 0
    i = pos
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2  # skip escaped character
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[pos + 1 : i], i + 1
        i += 1
    raise ValueError(f"Unbalanced braces starting at position {pos}")


def find_bracket_group(text: str, pos: int) -> tuple[str, int]:
    """Find a bracket-delimited group ``[...]`` starting at *pos*.

    Returns:
        ``(content, end)`` where *content* is everything between the
        brackets and *end* is the index just past ``]``.

    Raises:
        ValueError: If *pos* doesn't point to ``[`` or brackets are unbalanced.
    """
    if pos >= len(text) or text[pos] != "[":
        raise ValueError(f"Expected '[' at position {pos}")
    depth = 0
    i = pos
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[pos + 1 : i], i + 1
        i += 1
    raise ValueError(f"Unbalanced brackets starting at position {pos}")


def _skip_whitespace(text: str, pos: int) -> int:
    """Skip whitespace characters starting at *pos*."""
    while pos < len(text) and text[pos] in " \t\n\r":
        pos += 1
    return pos


# -----------------------------------------------------------------------
# Command extraction helpers
# -----------------------------------------------------------------------

# Matches \commandname (with backslash) — captures the name without \.
_CMD_RE = re.compile(r"\\([a-zA-Z]+)")


def _find_all_commands(text: str, cmd_name: str) -> list[int]:
    """Return starting positions of all occurrences of ``\\cmd_name``."""
    pattern = re.compile(r"\\" + re.escape(cmd_name) + r"(?![a-zA-Z])")
    return [m.start() for m in pattern.finditer(text)]


def _extract_one_arg(text: str, cmd_name: str) -> list[str]:
    r"""Extract the single mandatory argument from each ``\cmd{arg}``."""
    results = []
    for pos in _find_all_commands(text, cmd_name):
        i = pos + len(cmd_name) + 1  # skip \cmdname
        i = _skip_whitespace(text, i)
        if i < len(text) and text[i] == "{":
            content, _ = find_brace_group(text, i)
            results.append(content)
    return results


def _extract_texfrog_package_option(text: str) -> str | None:
    r"""Extract ``package=X`` from ``\usepackage[...]{texfrog}``."""
    m = re.search(r"\\usepackage\s*\[([^\]]*)\]\s*\{texfrog\}", text)
    if m:
        pm = re.search(r"(?:^|,)\s*package\s*=\s*(\w+)", m.group(1))
        if pm:
            return pm.group(1)
    return None


def _extract_two_args(text: str, cmd_name: str) -> list[tuple[str, str]]:
    r"""Extract both arguments from each ``\cmd{arg1}{arg2}``."""
    results = []
    for pos in _find_all_commands(text, cmd_name):
        i = pos + len(cmd_name) + 1
        i = _skip_whitespace(text, i)
        if i < len(text) and text[i] == "{":
            arg1, i = find_brace_group(text, i)
            i = _skip_whitespace(text, i)
            if i < len(text) and text[i] == "{":
                arg2, _ = find_brace_group(text, i)
                results.append((arg1, arg2))
    return results


def _extract_opt_two_args(
    text: str, cmd_name: str,
) -> list[tuple[Optional[str], str, str]]:
    r"""Extract ``\cmd[opt]{arg1}{arg2}`` — optional + 2 mandatory."""
    results = []
    for pos in _find_all_commands(text, cmd_name):
        i = pos + len(cmd_name) + 1
        i = _skip_whitespace(text, i)
        opt: Optional[str] = None
        if i < len(text) and text[i] == "[":
            opt, i = find_bracket_group(text, i)
            i = _skip_whitespace(text, i)
        if i < len(text) and text[i] == "{":
            arg1, i = find_brace_group(text, i)
            i = _skip_whitespace(text, i)
            if i < len(text) and text[i] == "{":
                arg2, _ = find_brace_group(text, i)
                results.append((opt, arg1, arg2))
    return results


# -----------------------------------------------------------------------
# tfsource extraction
# -----------------------------------------------------------------------

_TFSOURCE_BEGIN = re.compile(
    r"\\begin\s*\{tfsource\}\s*\{([^}]*)\}",
)
_TFSOURCE_END = re.compile(r"\\end\s*\{tfsource\}")


def _extract_tfsource(text: str) -> dict[str, str]:
    """Extract all ``\\begin{tfsource}{name}...\\end{tfsource}`` blocks.

    Returns a dict mapping source name to body text.
    """
    sources: dict[str, str] = {}
    for m in _TFSOURCE_BEGIN.finditer(text):
        name = m.group(1).strip()
        body_start = m.end()
        end_m = _TFSOURCE_END.search(text, body_start)
        if end_m is None:
            raise ValueError(
                f"Unterminated \\begin{{tfsource}}{{{name}}} — "
                f"missing \\end{{tfsource}}."
            )
        sources[name] = text[body_start : end_m.start()]
    return sources


# -----------------------------------------------------------------------
# \tfonly resolution
# -----------------------------------------------------------------------

_TFONLY_RE = re.compile(r"\\tfonly\*?(?![a-zA-Z])")
_TFONLY_STAR_RE = re.compile(r"\\tfonly\*(?![a-zA-Z])")
_TFFIGONLY_RE = re.compile(r"\\tffigonly(?![a-zA-Z])")


def resolve_tfonly(
    source_text: str,
    game_label: str,
    ordered_labels: list[str],
    *,
    strip_star: bool = False,
) -> str:
    r"""Resolve ``\tfonly``, ``\tfonly*``, and ``\tffigonly`` for a game.

    Walks through *source_text* and for each ``\tfonly`` or ``\tfonly*``:
    * If *game_label* is in the resolved tag set → replaces with *content*.
    * Otherwise → replaces with empty string.

    ``\tffigonly{content}`` is always stripped (it only appears in LaTeX
    consolidated figures, not in per-game rendering).

    Non-``\tfonly`` text passes through unchanged.

    Args:
        source_text: Raw body of a ``tfsource`` environment.
        game_label: The game to resolve for.
        ordered_labels: Ordered list of all game labels (for range resolution).
        strip_star: If ``True``, ``\tfonly*`` blocks are stripped entirely
            (replaced with empty string regardless of tags).  This is used
            for diff computation so that per-game header content does not
            participate in change detection.

    Returns:
        The resolved LaTeX string for the given game.
    """
    # First, strip all \tffigonly{...} calls (figure-only content)
    source_text = _strip_tffigonly(source_text)
    # Optionally strip \tfonly* blocks (for diff computation)
    if strip_star:
        source_text = _strip_tfonly_star(source_text)

    result: list[str] = []
    pos = 0
    for m in _TFONLY_RE.finditer(source_text):
        # Append text before this \tfonly
        result.append(source_text[pos : m.start()])
        # Parse the two brace groups: {tags}{content}
        i = m.end()
        i = _skip_whitespace(source_text, i)
        if i >= len(source_text) or source_text[i] != "{":
            raise ValueError(
                f"Expected '{{' after \\tfonly at position {m.start()}"
            )
        tag_str, i = find_brace_group(source_text, i)
        i = _skip_whitespace(source_text, i)
        if i >= len(source_text) or source_text[i] != "{":
            raise ValueError(
                f"Expected second '{{' after \\tfonly tags at position {m.start()}"
            )
        content, i = find_brace_group(source_text, i)
        # Resolve tags and check membership
        resolved = resolve_tag_ranges(tag_str, ordered_labels)
        if game_label in resolved:
            result.append(content)
        pos = i
    # Append remaining text after last \tfonly
    result.append(source_text[pos:])
    return "".join(result)


def _strip_tfonly_star(source_text: str) -> str:
    r"""Remove all ``\tfonly*{tags}{content}`` calls from source text."""
    result: list[str] = []
    pos = 0
    for m in _TFONLY_STAR_RE.finditer(source_text):
        result.append(source_text[pos : m.start()])
        i = m.end()
        i = _skip_whitespace(source_text, i)
        if i < len(source_text) and source_text[i] == "{":
            _, i = find_brace_group(source_text, i)  # skip tags
        i = _skip_whitespace(source_text, i)
        if i < len(source_text) and source_text[i] == "{":
            _, i = find_brace_group(source_text, i)  # skip content
        pos = i
    result.append(source_text[pos:])
    return "".join(result)


def _strip_tffigonly(source_text: str) -> str:
    r"""Remove all ``\tffigonly{content}`` calls from source text."""
    result: list[str] = []
    pos = 0
    for m in _TFFIGONLY_RE.finditer(source_text):
        result.append(source_text[pos : m.start()])
        i = m.end()
        i = _skip_whitespace(source_text, i)
        if i < len(source_text) and source_text[i] == "{":
            _, i = find_brace_group(source_text, i)
        pos = i
    result.append(source_text[pos:])
    return "".join(result)


# -----------------------------------------------------------------------
# SourceLine conversion (for compatibility with filter.py pipeline)
# -----------------------------------------------------------------------

def _source_text_to_lines(
    source_text: str,
    ordered_labels: list[str],
) -> list[SourceLine]:
    r"""Convert tfsource body into SourceLine objects.

    Each ``\tfonly{tags}{content}`` becomes one or more SourceLines with
    the appropriate tag set.  Bare text (between ``\tfonly`` calls) becomes
    SourceLines with ``tags=None``.

    This is used by the HTML pipeline which still relies on SourceLine-based
    filtering for the removed-lines view.
    """
    lines: list[SourceLine] = []
    # Strip \tffigonly calls first
    source_text = _strip_tffigonly(source_text)
    pos = 0
    for m in _TFONLY_RE.finditer(source_text):
        # Bare text before this \tfonly
        bare = source_text[pos : m.start()]
        for raw_line in bare.split("\n"):
            lines.append(SourceLine(content=raw_line, tags=None, original=raw_line))

        # Parse \tfonly{tags}{content}
        i = m.end()
        i = _skip_whitespace(source_text, i)
        tag_str, i = find_brace_group(source_text, i)
        i = _skip_whitespace(source_text, i)
        content, i = find_brace_group(source_text, i)
        resolved = resolve_tag_ranges(tag_str, ordered_labels)
        for raw_line in content.split("\n"):
            lines.append(
                SourceLine(content=raw_line, tags=resolved, original=raw_line)
            )
        pos = i

    # Remaining bare text
    bare = source_text[pos:]
    for raw_line in bare.split("\n"):
        lines.append(SourceLine(content=raw_line, tags=None, original=raw_line))

    return lines


# -----------------------------------------------------------------------
# Main parser
# -----------------------------------------------------------------------

_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_-]+$")


def parse_tex_proof(tex_path: Path) -> Proof:
    r"""Parse a ``.tex`` file containing TeXFrog commands into a Proof.

    Extracts:
    * ``\tfgames{...}`` — ordered game labels.
    * ``\tfgamename{label}{name}`` — display names.
    * ``\tfdescription{label}{text}`` — game descriptions.
    * ``\tfreduction{label}`` — reduction flags.
    * ``\tfrelatedgames{label}{games}`` — related games for reductions.
    * ``\usepackage[package=name]{texfrog}`` — package profile.
    * ``\tfmacrofile{path}`` — macro file paths.
    * ``\tfpreamble{path}`` — extra preamble file.
    * ``\tfcommentary{label}{path}`` — commentary file paths.
    * ``\tffigure[name]{label}{games}`` — figure specifications.
    * ``\\begin{tfsource}{name}...\\end{tfsource}`` — proof source.

    Args:
        tex_path: Path to the ``.tex`` file.

    Returns:
        A fully populated :class:`Proof` instance.

    Raises:
        FileNotFoundError: If referenced files don't exist.
        ValueError: If required fields are missing or invalid.
    """
    tex_path = Path(tex_path).resolve()
    base_dir = tex_path.parent
    text = tex_path.read_text(encoding="utf-8")

    # --- package ---
    package_name = _extract_texfrog_package_option(text) or "cryptocode"
    get_profile(package_name)  # validate

    # --- games ---
    games_lists = _extract_one_arg(text, "tfgames")
    if not games_lists:
        raise ValueError(
            r"\tfgames{...} not found. Define games with "
            r"\tfgames{G0, G1, ...} in the preamble."
        )
    ordered_labels = [
        label.strip()
        for label in games_lists[-1].split(",")
        if label.strip()
    ]
    if not ordered_labels:
        raise ValueError(r"\tfgames{...} is empty.")
    for label in ordered_labels:
        if not _SAFE_LABEL.match(label):
            raise ValueError(
                f"Game label '{label}' contains unsafe characters. "
                f"Labels must match [A-Za-z0-9_-]."
            )

    # --- game names ---
    name_pairs = _extract_two_args(text, "tfgamename")
    name_map: dict[str, str] = {}
    for label, name in name_pairs:
        label = label.strip()
        name_map[label] = name.strip()

    # --- descriptions ---
    desc_pairs = _extract_two_args(text, "tfdescription")
    desc_map: dict[str, str] = {}
    for label, desc in desc_pairs:
        desc_map[label.strip()] = desc.strip()

    # --- reductions ---
    reduction_labels = set()
    for label in _extract_one_arg(text, "tfreduction"):
        reduction_labels.add(label.strip())

    # --- related games ---
    related_map: dict[str, list[str]] = {}
    for label, games_str in _extract_two_args(text, "tfrelatedgames"):
        related_map[label.strip()] = [
            g.strip() for g in games_str.split(",") if g.strip()
        ]

    # Build Game objects
    games: list[Game] = []
    for label in ordered_labels:
        latex_name = name_map.get(label, label)
        description = desc_map.get(label, "")
        is_reduction = label in reduction_labels
        related = related_map.get(label, [])
        if related and not is_reduction:
            raise ValueError(
                f"Game '{label}' has \\tfrelatedgames but is not a reduction. "
                f"\\tfrelatedgames is only valid for reductions."
            )
        if len(related) > 2:
            raise ValueError(
                f"Reduction '{label}' has {len(related)} related games "
                f"(maximum is 2)."
            )
        for ref in related:
            if ref not in ordered_labels:
                raise ValueError(
                    f"Reduction '{label}' references unknown related game "
                    f"'{ref}'. Available labels: {ordered_labels}"
                )
        games.append(Game(
            label=label,
            latex_name=latex_name,
            description=description,
            reduction=is_reduction,
            related_games=related,
        ))

    # --- macros ---
    macros: list[str] = _extract_one_arg(text, "tfmacrofile")
    for macro_rel in macros:
        macro_path = (base_dir / macro_rel.strip()).resolve()
        if not macro_path.is_relative_to(base_dir):
            raise ValueError(
                f"Macro path '{macro_rel}' resolves outside the proof directory."
            )

    # --- preamble ---
    preambles = _extract_one_arg(text, "tfpreamble")
    preamble_rel: Optional[str] = preambles[-1].strip() if preambles else None
    if preamble_rel:
        preamble_path = (base_dir / preamble_rel).resolve()
        if not preamble_path.is_relative_to(base_dir):
            raise ValueError(
                f"Preamble path '{preamble_rel}' resolves outside the proof directory."
            )
        if not preamble_path.exists():
            raise FileNotFoundError(
                f"Preamble file '{preamble_rel}' not found (looked in {base_dir}/)."
            )

    # --- commentary ---
    commentary_pairs = _extract_two_args(text, "tfcommentary")
    commentary: dict[str, str] = {}
    commentary_files: dict[str, str] = {}
    for label, file_rel in commentary_pairs:
        label = label.strip()
        file_rel = file_rel.strip()
        file_path = (base_dir / file_rel).resolve()
        if not file_path.is_relative_to(base_dir):
            raise ValueError(
                f"Commentary path '{file_rel}' for '{label}' resolves "
                f"outside the proof directory."
            )
        if not file_path.exists():
            raise FileNotFoundError(
                f"Commentary file '{file_rel}' for '{label}' not found "
                f"(looked in {base_dir}/)."
            )
        commentary[label] = file_path.read_text(encoding="utf-8")
        commentary_files[label] = file_rel

    # --- figures ---
    figure_entries = _extract_opt_two_args(text, "tffigure")
    figures: list[Figure] = []
    for proc_name, label, games_str in figure_entries:
        label = label.strip()
        if not _SAFE_LABEL.match(label):
            raise ValueError(
                f"Figure label '{label}' contains unsafe characters."
            )
        resolved = list(resolve_tag_ranges(games_str, ordered_labels))
        ordered_figure_games = [l for l in ordered_labels if l in resolved]
        figures.append(Figure(
            label=label,
            games=ordered_figure_games,
            procedure_name=proc_name,
        ))

    # --- source ---
    sources = _extract_tfsource(text)
    if not sources:
        raise ValueError(
            r"No \begin{tfsource} found. Define proof source with "
            r"\begin{tfsource}{name}...\end{tfsource}."
        )
    # Use the first source block (most proofs have one)
    source_name = next(iter(sources))
    source_text = sources[source_name]

    return Proof(
        macros=[m.strip() for m in macros],
        games=games,
        source_lines=[],  # Not used for .tex format; use source_text instead
        commentary=commentary,
        figures=figures,
        package=package_name,
        preamble=preamble_rel,
        commentary_files=commentary_files,
        source_text=source_text,
    )


def filter_for_game_from_text(
    source_text: str,
    game_label: str,
    ordered_labels: list[str],
    *,
    strip_star: bool = False,
) -> list[str]:
    r"""Resolve ``\tfonly`` calls and return filtered lines for a game.

    This is the ``\tfonly``-format equivalent of
    :func:`~texfrog.filter.filter_for_game`.  It resolves all ``\tfonly``
    calls for the given game, splits into lines, and strips trailing ``\\``
    from the last non-empty line.

    Args:
        source_text: Raw body of a ``tfsource`` environment.
        game_label: The game to resolve for.
        ordered_labels: Ordered list of all game labels.
        strip_star: If ``True``, ``\tfonly*`` blocks are stripped entirely
            so their content does not appear in the output.  Used for diff
            computation (game headers should not be highlighted).

    Returns:
        List of content strings for the game.
    """
    from .filter import _strip_trailing_newline_sep

    resolved = resolve_tfonly(
        source_text, game_label, ordered_labels, strip_star=strip_star,
    )
    lines = resolved.split("\n")
    return _strip_trailing_newline_sep(lines)
