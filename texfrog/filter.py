"""Line filtering and diff computation for TeXFrog."""

from __future__ import annotations

import difflib
import re

from .model import SourceLine

# Matches a trailing \\ possibly followed by whitespace at end of a line.
_TRAILING_BACKSLASH_BS = re.compile(r"\\\\(\s*)$")

# Matches a trailing % (LaTeX newline suppressor) at end of a line.
# This must be placed outside wrapping macros to avoid commenting out the
# closing brace: \tfchanged{content}% instead of \tfchanged{content%}.
_TRAILING_PERCENT = re.compile(r"(?<!\\)%(\s*)$")

# Matches a \item prefix (nicodemus-style) with optional leading whitespace.
_ITEM_PREFIX = re.compile(r"^(\s*\\item\s*)")


def _strip_trailing_newline_sep(lines: list[str]) -> list[str]:
    """Strip trailing \\ from the last non-empty line in a list.

    In cryptocode-style pseudocode, every line except the last ends with
    ``\\``.  After filtering, the last *included* line may have ended with
    ``\\`` in the combined source (because more lines follow in other games).
    This function removes it to produce valid LaTeX.

    For packages like algorithmicx that don't use ``\\`` as a separator, the
    last line won't end with ``\\``, so this function is a no-op.

    Args:
        lines: Filtered content lines (no tag comments).

    Returns:
        Lines with trailing ``\\`` stripped from the last non-empty line.
    """
    result = list(lines)
    for i in range(len(result) - 1, -1, -1):
        stripped = result[i].rstrip()
        if stripped:
            m = _TRAILING_BACKSLASH_BS.search(stripped)
            if m:
                result[i] = stripped[: m.start()]
            break
    return result


def filter_for_game(source_lines: list[SourceLine], label: str) -> list[str]:
    """Return the filtered list of content lines for the given game label.

    A line is included if:
    * Its ``tags`` field is ``None`` (untagged — appears in all games), OR
    * The given ``label`` is in its ``tags`` set.

    The ``%:tags:`` comment has already been stripped from ``SourceLine.content``
    by the parser.  This function returns those content strings, with the
    trailing ``\\`` removed from the last non-empty included line (see
    :func:`_strip_trailing_newline_sep`).

    Args:
        source_lines: All lines from the combined source file.
        label: The game/reduction label to filter for.

    Returns:
        List of content strings for the game, ready to be written to a file.
    """
    included: list[str] = []
    for sl in source_lines:
        if sl.tags is None or label in sl.tags:
            included.append(sl.content)
    return _strip_trailing_newline_sep(included)


def compute_removed_lines(prev_lines: list[str], curr_lines: list[str]) -> set[int]:
    """Compute which lines in ``prev_lines`` are deleted or replaced in ``curr_lines``.

    Uses :class:`difflib.SequenceMatcher` to align the two sequences and
    identifies lines in ``prev_lines`` that are *deletions* or *replacements*
    (i.e., present in ``prev`` but not matched to an equal line in ``curr``).

    Args:
        prev_lines: Filtered lines for the previous game.
        curr_lines: Filtered lines for the current game.

    Returns:
        A set of 0-based indices into ``prev_lines`` that are removed or changed.
    """
    if not prev_lines:
        return set()

    removed: set[int] = set()
    matcher = difflib.SequenceMatcher(None, prev_lines, curr_lines, autojunk=False)
    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            removed.update(range(i1, i2))
    return removed


def compute_changed_lines(prev_lines: list[str], curr_lines: list[str]) -> set[int]:
    """Compute which lines in ``curr_lines`` are new or changed relative to ``prev_lines``.

    Uses :class:`difflib.SequenceMatcher` to align the two sequences and
    identifies lines in ``curr_lines`` that are *insertions* or *replacements*
    (i.e., present in ``curr`` but not matched to an equal line in ``prev``).

    Args:
        prev_lines: Filtered lines for the previous game (or ``[]`` for the
            first game, which has no changes to highlight).
        curr_lines: Filtered lines for the current game.

    Returns:
        A set of 0-based indices into ``curr_lines`` that are new or changed.
    """
    if not prev_lines:
        return set()

    changed: set[int] = set()
    matcher = difflib.SequenceMatcher(None, prev_lines, curr_lines, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("insert", "replace"):
            changed.update(range(j1, j2))
    return changed


def wrap_changed_line(
    line: str,
    macro: str = r"\tfchanged",
    procedure_header_cmd: str | None = None,
) -> str:
    r"""Wrap a changed pseudocode line with a highlighting macro.

    Several kinds of lines are returned **verbatim** (never wrapped):

    * Pure comment lines (starting with ``%``)
    * Lines ending with ``{`` (or ``{%``) — structural brace openers
      (procedure headers, ``\nicodemusbox{...}{%``)
    * ``\markersetlen`` lines — layout-only dimension commands
    * ``\begin{...}`` / ``\end{...}`` lines — environment boundaries

    For lines ending with ``\\`` (cryptocode-style line separator), the
    ``\\`` is placed *outside* the macro call so the macro only wraps the
    visual content:

        \tfchanged{\key_1 \gets ...} \\

    For lines starting with ``\item`` (nicodemus-style), the ``\item``
    prefix is placed *outside* the macro call:

        \item \tfchanged{$content$}

    For lines ending with ``%`` (LaTeX newline suppressor), the ``%`` is
    placed *outside* the macro call so it does not comment out the closing
    brace:

        \tfchanged{content}%

    For lines without a trailing ``\\`` (last line of a procedure, or lines
    in algorithmicx-style packages):

        \tfchanged{\State $\key_1 \gets ...$}

    Args:
        line: A single content line (no tag comment).
        macro: The LaTeX macro name to use for wrapping (default ``\tfchanged``).

    Returns:
        The wrapped line string.
    """
    stripped = line.rstrip()
    # Don't wrap pure comment lines (content is a LaTeX comment) — they are
    # invisible in the compiled PDF and wrapping them produces spurious output.
    if stripped.lstrip().startswith("%"):
        return line
    # Strip a trailing % (LaTeX newline suppressor) for the structural checks
    # below, so that e.g. \nicodemusbox{...}{% is correctly recognised as
    # ending with '{'.
    core = stripped.rstrip("%").rstrip()
    trimmed = stripped.lstrip()
    # Don't wrap lines that open a LaTeX group with an unmatched '{' (e.g.
    # \procedure{Name}{ or \nicodemusbox{...}{%) — wrapping them would break
    # LaTeX brace-matching.  Such structural lines are returned verbatim.
    if core.endswith("{"):
        return line
    # Don't wrap procedure header lines identified by a package-specific
    # command (e.g. \nicodemusheader{...}).
    if procedure_header_cmd and trimmed.startswith(f"\\{procedure_header_cmd}{{"):
        return line
    # Don't wrap layout-only commands that control column/box dimensions.
    # These vary between games but are not proof content.
    if trimmed.startswith(r"\markersetlen"):
        return line
    # Don't wrap environment boundaries (\begin{...} / \end{...}) when they
    # appear as standalone structural lines.  Wrapping \begin{nicodemus}
    # in \tfchanged would start the environment inside an \adjustbox, then
    # the closing } of \tfchanged would close the box while the environment
    # remains open — breaking LaTeX grouping.
    if trimmed.startswith(r"\begin{") or trimmed.startswith(r"\end{"):
        return line

    # Extract \item prefix if present (nicodemus-style enumerate lines).
    # The \item must stay outside the wrapping macro so the list structure
    # is preserved.
    item_match = _ITEM_PREFIX.match(line)
    if item_match:
        prefix = item_match.group(0)
        rest = line[item_match.end():]
    else:
        prefix = ""
        rest = line

    stripped_rest = rest.rstrip()
    m = _TRAILING_BACKSLASH_BS.search(stripped_rest)
    if m:
        content = rest[: m.start()].rstrip()
        return f"{prefix}{macro}{{{content}}} \\\\"
    else:
        # Check for trailing % (LaTeX newline suppressor).  If left inside
        # the macro, it comments out the closing brace:
        #   \tfchanged{content%}  ← LaTeX never sees the }
        # Move it outside: \tfchanged{content}%
        pm = _TRAILING_PERCENT.search(stripped_rest)
        if pm:
            content = rest[:pm.start()].rstrip()
            return f"{prefix}{macro}{{{content}}}%"
        return f"{prefix}{macro}{{{rest}}}"
