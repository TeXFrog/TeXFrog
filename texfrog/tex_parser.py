"""Parse TeXFrog commands from .tex files.

Extracts game definitions, source content, and metadata from a LaTeX file
that uses the texfrog.sty package.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .model import Figure, Game, Proof
from .packages import get_profile


# -----------------------------------------------------------------------
# Tag range resolution
# -----------------------------------------------------------------------

def resolve_tag_ranges(tag_string: str, ordered_labels: list[str]) -> frozenset[str]:
    """Convert a tag string like "G0,G3-G5" to a frozenset of labels.

    Ranges are resolved by position in ``ordered_labels``.  A range
    "A-B" includes every label from A to B inclusive (in list order).
    Single labels outside the ordered list are still accepted verbatim
    (they simply never match any game and are therefore silently ignored
    at filtering time).

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
                result.add(token)
        else:
            result.add(token)

    return frozenset(result)


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


def _extract_three_args(
    text: str, cmd_name: str,
) -> list[tuple[str, str, str]]:
    r"""Extract all three arguments from each ``\cmd{arg1}{arg2}{arg3}``."""
    results = []
    for pos in _find_all_commands(text, cmd_name):
        i = pos + len(cmd_name) + 1
        i = _skip_whitespace(text, i)
        if i < len(text) and text[i] == "{":
            arg1, i = find_brace_group(text, i)
            i = _skip_whitespace(text, i)
            if i < len(text) and text[i] == "{":
                arg2, i = find_brace_group(text, i)
                i = _skip_whitespace(text, i)
                if i < len(text) and text[i] == "{":
                    arg3, _ = find_brace_group(text, i)
                    results.append((arg1, arg2, arg3))
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


def _extract_one_plus_opt_two_args(
    text: str, cmd_name: str,
) -> list[tuple[str, Optional[str], str, str]]:
    r"""Extract ``\cmd{source}[opt]{arg1}{arg2}`` — 1 mandatory + optional + 2 mandatory."""
    results = []
    for pos in _find_all_commands(text, cmd_name):
        i = pos + len(cmd_name) + 1
        i = _skip_whitespace(text, i)
        if i < len(text) and text[i] == "{":
            source, i = find_brace_group(text, i)
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
                    results.append((source, opt, arg1, arg2))
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
# Main parser
# -----------------------------------------------------------------------

_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_-]+$")


def parse_tex_proofs(tex_path: Path) -> list[Proof]:
    r"""Parse a ``.tex`` file containing TeXFrog commands into Proof objects.

    Supports multiple independent proofs per document.  Each proof is
    identified by its source name (from ``\begin{tfsource}{name}``).
    Metadata commands (``\tfgames``, ``\tfgamename``, etc.) take the
    source name as their first argument to associate them with a proof.

    Shared fields (``\tfmacrofile``, ``\tfpreamble``, package option) are
    the same across all proofs in the document.

    Args:
        tex_path: Path to the ``.tex`` file.

    Returns:
        A list of fully populated :class:`Proof` instances, one per
        ``tfsource`` block.

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

    # --- source blocks ---
    sources = _extract_tfsource(text)
    if not sources:
        raise ValueError(
            r"No \begin{tfsource} found. Define proof source with "
            r"\begin{tfsource}{name}...\end{tfsource}."
        )

    # --- games (per-source): \tfgames{source}{games} ---
    games_by_source: dict[str, list[str]] = {}
    for source, games_str in _extract_two_args(text, "tfgames"):
        source = source.strip()
        ordered = [l.strip() for l in games_str.split(",") if l.strip()]
        if not ordered:
            raise ValueError(rf"\tfgames{{{source}}}{{...}} is empty.")
        for label in ordered:
            if not _SAFE_LABEL.match(label):
                raise ValueError(
                    f"Game label '{label}' in source '{source}' contains "
                    f"unsafe characters. Labels must match [A-Za-z0-9_-]."
                )
        games_by_source[source] = ordered

    # --- game names (per-source): \tfgamename{source}{label}{name} ---
    names_by_source: dict[str, dict[str, str]] = {}
    for source, label, name in _extract_three_args(text, "tfgamename"):
        source = source.strip()
        names_by_source.setdefault(source, {})[label.strip()] = name.strip()

    # --- descriptions (per-source): \tfdescription{source}{label}{desc} ---
    descs_by_source: dict[str, dict[str, str]] = {}
    for source, label, desc in _extract_three_args(text, "tfdescription"):
        source = source.strip()
        descs_by_source.setdefault(source, {})[label.strip()] = desc.strip()

    # --- reductions (per-source): \tfreduction{source}{label} ---
    reductions_by_source: dict[str, set[str]] = {}
    for source, label in _extract_two_args(text, "tfreduction"):
        source = source.strip()
        reductions_by_source.setdefault(source, set()).add(label.strip())

    # --- related games (per-source): \tfrelatedgames{source}{label}{games} ---
    related_by_source: dict[str, dict[str, list[str]]] = {}
    for source, label, games_str in _extract_three_args(text, "tfrelatedgames"):
        source = source.strip()
        related_by_source.setdefault(source, {})[label.strip()] = [
            g.strip() for g in games_str.split(",") if g.strip()
        ]

    # --- macros (global) ---
    macros: list[str] = _extract_one_arg(text, "tfmacrofile")
    for macro_rel in macros:
        macro_path = (base_dir / macro_rel.strip()).resolve()
        if not macro_path.is_relative_to(base_dir):
            raise ValueError(
                f"Macro path '{macro_rel}' resolves outside the proof directory."
            )

    # --- preamble (global) ---
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

    # --- commentary (per-source): \tfcommentary{source}{label}{file} ---
    commentary_by_source: dict[str, dict[str, str]] = {}
    commentary_files_by_source: dict[str, dict[str, str]] = {}
    for source, label, file_rel in _extract_three_args(text, "tfcommentary"):
        source = source.strip()
        label = label.strip()
        file_rel = file_rel.strip()
        file_path = (base_dir / file_rel).resolve()
        if not file_path.is_relative_to(base_dir):
            raise ValueError(
                f"Commentary path '{file_rel}' for '{source}:{label}' resolves "
                f"outside the proof directory."
            )
        if not file_path.exists():
            raise FileNotFoundError(
                f"Commentary file '{file_rel}' for '{source}:{label}' not found "
                f"(looked in {base_dir}/)."
            )
        commentary_by_source.setdefault(source, {})[label] = \
            file_path.read_text(encoding="utf-8")
        commentary_files_by_source.setdefault(source, {})[label] = file_rel

    # --- figures (per-source): \tffigure{source}[opt]{label}{games} ---
    figures_by_source: dict[str, list[Figure]] = {}
    for source, proc_name, label, games_str in _extract_one_plus_opt_two_args(
        text, "tffigure",
    ):
        source = source.strip()
        label = label.strip()
        if not _SAFE_LABEL.match(label):
            raise ValueError(
                f"Figure label '{label}' in source '{source}' contains "
                f"unsafe characters."
            )
        ordered_labels = games_by_source.get(source, [])
        resolved = list(resolve_tag_ranges(games_str, ordered_labels))
        ordered_figure_games = [l for l in ordered_labels if l in resolved]
        figures_by_source.setdefault(source, []).append(Figure(
            label=label,
            games=ordered_figure_games,
            procedure_name=proc_name,
        ))

    # --- Build one Proof per source ---
    proofs: list[Proof] = []
    for source_name, source_text in sources.items():
        ordered_labels = games_by_source.get(source_name)
        if ordered_labels is None:
            raise ValueError(
                f"Source '{source_name}' has no \\tfgames definition. "
                f"Add \\tfgames{{{source_name}}}{{G0, G1, ...}}."
            )

        name_map = names_by_source.get(source_name, {})
        desc_map = descs_by_source.get(source_name, {})
        reduction_labels = reductions_by_source.get(source_name, set())
        related_map = related_by_source.get(source_name, {})

        games: list[Game] = []
        for label in ordered_labels:
            latex_name = name_map.get(label, label)
            description = desc_map.get(label, "")
            is_reduction = label in reduction_labels
            related = related_map.get(label, [])
            if related and not is_reduction:
                raise ValueError(
                    f"Game '{label}' in source '{source_name}' has "
                    f"\\tfrelatedgames but is not a reduction."
                )
            if len(related) > 2:
                raise ValueError(
                    f"Reduction '{label}' in source '{source_name}' has "
                    f"{len(related)} related games (maximum is 2)."
                )
            for ref in related:
                if ref not in ordered_labels:
                    raise ValueError(
                        f"Reduction '{label}' in source '{source_name}' "
                        f"references unknown related game '{ref}'. "
                        f"Available labels: {ordered_labels}"
                    )
            games.append(Game(
                label=label,
                latex_name=latex_name,
                description=description,
                reduction=is_reduction,
                related_games=related,
            ))

        proofs.append(Proof(
            source_name=source_name,
            macros=[m.strip() for m in macros],
            games=games,
            source_text=source_text,
            commentary=commentary_by_source.get(source_name, {}),
            figures=figures_by_source.get(source_name, []),
            package=package_name,
            preamble=preamble_rel,
            commentary_files=commentary_files_by_source.get(source_name, {}),
        ))

    return proofs


def parse_tex_proof(tex_path: Path) -> Proof:
    r"""Parse a ``.tex`` file into a single Proof.

    Convenience wrapper around :func:`parse_tex_proofs` for documents
    with exactly one ``tfsource`` block.

    Raises:
        ValueError: If the document contains zero or more than one proof.
    """
    proofs = parse_tex_proofs(tex_path)
    if len(proofs) != 1:
        raise ValueError(
            f"Expected exactly one proof, found {len(proofs)}. "
            f"Use parse_tex_proofs() for multi-proof documents."
        )
    return proofs[0]


def filter_for_game_from_text(
    source_text: str,
    game_label: str,
    ordered_labels: list[str],
    *,
    strip_star: bool = False,
) -> list[str]:
    r"""Resolve ``\tfonly`` calls and return filtered lines for a game.

    Resolves all ``\tfonly`` calls for the given game, splits into lines,
    and strips trailing ``\\`` from the last non-empty line.

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
