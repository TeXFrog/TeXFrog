"""Line filtering and diff computation for TeXFrog."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

# Matches a trailing \\ possibly followed by whitespace at end of a line.
_TRAILING_BACKSLASH_BS = re.compile(r"\\\\(\s*)$")

# Matches a trailing % (LaTeX newline suppressor) at end of a line.
# This must be placed outside wrapping macros to avoid commenting out the
# closing brace: \tfchanged{content}% instead of \tfchanged{content%}.
_TRAILING_PERCENT = re.compile(r"(?<!\\)%(\s*)$")

# Matches a \item prefix (nicodemus-style) with optional leading whitespace.
_ITEM_PREFIX = re.compile(r"^(\s*\\item\s*)")

# Matches a \State prefix (algorithmicx-style, e.g. algpseudocodex) with
# optional leading whitespace. The \b word boundary is required so this
# doesn't misparse \Statex (a distinct, common algorithmicx command for
# unnumbered continuation lines) as \State followed by stray "x ...".
_STATE_PREFIX = re.compile(r"^(\s*\\State\b\s*)")

# Matches a pseudocode line that algpseudocodex counts as a NUMBERED line
# (with the `[1]` line-numbering option). Every statement/block command
# numbers; \Statex (unnumbered continuation) does not -- the \b after State
# excludes \Statex, since "State" is immediately followed by the word char
# "x" there, so no word boundary matches. This assumes default algpseudocodex
# numbering (no ``noEnd`` option, under which \End... lines would not number);
# it is used only to reproduce the LaTeX crop-render's ABSOLUTE line numbers
# in the HTML output. The PDF uses the real ALG@line counter and is always
# exact; the HTML relies on this heuristic matching it.
_NUMBERED_LINE_RE = re.compile(
    r"^\s*\\(?:State|If|ElsIf|Else|For|ForAll|While|Repeat|Until|Loop"
    r"|EndLoop|Function|Procedure|EndFunction|EndProcedure|EndIf|EndFor"
    r"|EndWhile|Require|Ensure|Return)\b"
)

# Matches a \tfsegment{caption} marker line (optional leading whitespace).
# The caption charset is ``[^{}]*`` to stay in parity with the LaTeX-side
# marker regex in ``texfrog.sty`` (``\c{tfsegment} \{ [^\{\}]* \}``): a caption
# containing braces would otherwise be split differently in the HTML and PDF
# builds. (The line anchoring here mirrors the convention that a marker sits on
# its own line.)
_SEGMENT_RE = re.compile(r"^\s*\\tfsegment\s*\{(?P<caption>[^{}]*)\}\s*$")
SEGMENT_RE = _SEGMENT_RE

# \begin{name} / \end{name} environment delimiter, used to peel the final
# segment's trailing closer off from its content (see below). Lowercase
# ``begin``/``end`` only, so algpseudocodex block openers/closers like
# ``\If``/``\EndIf`` are NOT treated as environment delimiters.
_ENV_DELIM_RE = re.compile(r"\\(begin|end)\s*\{([^{}]*)\}")
# A line that is (starts as) ``\end{name}``.
_END_ENV_RE = re.compile(r"^\s*\\end\s*\{([^{}]*)\}")


@dataclass
class Segment:
    """A run of content lines between two \\tfsegment markers."""

    caption: str | None  # None for the implicit preamble segment (segment 0)
    lines: list[str] = field(default_factory=list)


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
    matcher = difflib.SequenceMatcher(
        lambda x: not x.strip(), prev_lines, curr_lines, autojunk=False,
    )
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
    matcher = difflib.SequenceMatcher(
        lambda x: not x.strip(), prev_lines, curr_lines, autojunk=False,
    )
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

    For lines starting with ``\State`` (algorithmicx-style packages, e.g.
    algpseudocodex), the ``\State`` prefix is placed *outside* the macro
    call, exactly like ``\item``:

        \State \tfchanged{$\key_1 \gets ...$}

    (``\State``'s internals do real vertical-mode box/prevdepth bookkeeping
    that breaks if nested inside the highlight box, so it cannot be wrapped
    along with its content the way plain math/text can.)

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
    # Don't wrap structural box commands (\nicodemusbox, \nicodemusboxNew).
    # These take a second argument on the following line ({%...}%) and
    # wrapping them in \tfchanged would steal that argument's closing brace.
    if trimmed.startswith(r"\nicodemusbox"):
        return line
    # Don't wrap environment boundaries (\begin{...} / \end{...}) when they
    # appear as standalone structural lines.  Wrapping \begin{nicodemus}
    # in \tfchanged would start the environment inside an \adjustbox, then
    # the closing } of \tfchanged would close the box while the environment
    # remains open — breaking LaTeX grouping.
    if trimmed.startswith(r"\begin{") or trimmed.startswith(r"\end{"):
        return line

    # Extract a \item (nicodemus) or \State (algorithmicx-style) prefix if
    # present. Both must stay outside the wrapping macro: \item to preserve
    # list structure, \State because its box/prevdepth internals break if
    # nested inside the highlight box.
    item_match = _ITEM_PREFIX.match(line)
    state_match = _STATE_PREFIX.match(line)
    if item_match:
        prefix = item_match.group(0)
        rest = line[item_match.end():]
    elif state_match:
        prefix = state_match.group(0)
        rest = line[state_match.end():]
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


def split_into_segments(lines: list[str]) -> list[Segment]:
    """Split filtered content lines into segments at \\tfsegment markers.

    Content before the first marker is segment 0 with ``caption=None``.
    Marker lines are consumed (not included in any segment's ``lines``).

    Args:
        lines: Filtered content lines for one game (may contain markers).

    Returns:
        A list of :class:`Segment`, always at least one element long.
    """
    segments: list[Segment] = [Segment(caption=None)]
    for line in lines:
        m = _SEGMENT_RE.match(line)
        if m:
            segments.append(Segment(caption=m.group("caption").strip()))
        else:
            segments[-1].lines.append(line)
    return segments


def _seg_content(seg: Segment) -> list[str]:
    """Non-blank content lines of a segment (blank lines ignored for diffing)."""
    return [ln for ln in seg.lines if ln.strip()]


def _count_numbered_lines(lines: list[str]) -> int:
    """Count algpseudocodex-numbered lines in a list of source lines.

    See :data:`_NUMBERED_LINE_RE` for what counts as numbered.
    """
    return sum(1 for ln in lines if _NUMBERED_LINE_RE.match(ln))


def compute_active_segments(
    target_lines: list[str], curr_lines: list[str]
) -> set[int]:
    """Indices of current segments that differ from the aligned target segment.

    Segment i in ``curr_lines`` aligns with segment i in ``target_lines`` (the
    \\tfsegment marker sequence is identical across games). A segment is active
    if its non-blank content differs, or (when it has no target counterpart) if
    it contains any non-blank line.

    Segment 0 (preamble) is reported like any other; callers keep it regardless.

    Args:
        target_lines: Filtered lines of the diff-target game.
        curr_lines: Filtered lines of the current game.

    Returns:
        Set of 0-based active segment indices into the current segmentation.
    """
    target_segs = split_into_segments(target_lines)
    curr_segs = split_into_segments(curr_lines)
    active: set[int] = set()
    for i, seg in enumerate(curr_segs):
        tgt = _seg_content(target_segs[i]) if i < len(target_segs) else []
        if _seg_content(seg) != tgt:
            active.add(i)
    return active


def _outer_open_env(preamble_lines: list[str]) -> str | None:
    """The innermost environment left open by the preamble (segment 0), if any.

    Segment 0 holds the source's opening ``\\begin{...}`` (e.g. ``algorithmic``
    or ``pcvstack``); the final segment closes it with the matching
    ``\\end{...}``. Returns that environment's name so the closer peel matches
    *only* it — never an inner ``\\end{align}`` / ``\\end{cases}`` sitting in a
    math line of the final segment's content.
    """
    stack: list[str] = []
    for ln in preamble_lines:
        for m in _ENV_DELIM_RE.finditer(ln):
            if m.group(1) == "begin":
                stack.append(m.group(2))
            elif stack and stack[-1] == m.group(2):
                stack.pop()
    return stack[-1] if stack else None


def _split_trailing_closer(
    lines: list[str], env: str | None
) -> tuple[list[str], list[str]]:
    """Split ``lines`` into ``(content, closer)`` at the trailing env closer.

    ``closer`` is the maximal trailing run of blank lines and ``\\end{env}``
    lines — where ``env`` is the outer environment from :func:`_outer_open_env`;
    ``content`` is everything before it. Returns ``(lines, [])`` (nothing to
    peel) when ``env`` is ``None`` or the tail is not ``\\end{env}``, signalling
    the caller it cannot safely crop this segment.
    """
    if env is None:
        return lines, []
    i = len(lines)
    while i > 0:
        ln = lines[i - 1]
        if not ln.strip():
            i -= 1
            continue
        m = _END_ENV_RE.match(ln)
        if m and m.group(1) == env:
            i -= 1
            continue
        break
    return lines[:i], lines[i:]


def crop_to_active_segments(
    lines: list[str],
    active: set[int],
    stub_macro: str = r"\tfsegmentstub",
    line_counter: str | None = None,
) -> tuple[list[str], list[int]]:
    """Rebuild ``lines`` keeping active segments, stubbing inactive ones.

    Segment 0 (preamble, typically the opening ``\\begin{...}``) is always kept
    verbatim. The final segment is split at its trailing environment closer
    (:func:`_split_trailing_closer`): the ``\\end{...}`` run is always kept so
    the environment stays balanced, but the final segment's leading *content*
    crops like any interior segment — stubbed when inactive, kept when active.
    This matches the LaTeX macro ``\\__tf_seg_render_one:n`` in ``texfrog.sty``.
    (If the final segment has no separable ``\\end{...}`` tail, it is kept
    verbatim as a safe fallback.) Each strictly-interior inactive segment
    (index in ``1..len(segs) - 2``) collapses to its own
    ``\\tfsegmentstub{caption}`` line — one stub per segment, each on its own
    line, so a run of several unchanged segments produces several stub lines
    rather than a single comma-joined one (a blank/None caption yields an
    empty stub argument).

    When ``line_counter`` is given (e.g. ``"ALG@line"`` for algpseudocodex), a
    ``\\setcounter{<line_counter>}{N}`` line is inserted before each kept
    segment after segment 0, where ``N`` is the number of numbered lines in all
    preceding segments of the *full* (uncropped) input. This gives kept lines
    their ABSOLUTE numbers from the full listing (numbers jump across a stub),
    mirroring the LaTeX crop-render's line-count pass. Injected lines get an
    ``idx_map`` entry of ``-1``, like stubs.

    Args:
        lines: Filtered content lines (with markers) for the current game.
        active: Active segment indices from :func:`compute_active_segments`.
        stub_macro: Macro name emitted for a stubbed segment.
        line_counter: LaTeX line-number counter name to reset per kept segment
            for absolute numbering, or ``None`` to disable (no injection).

    Returns:
        ``(new_lines, idx_map)`` where ``idx_map[k]`` is the original index of
        ``new_lines[k]`` in ``lines``, or ``-1`` for a synthesized stub or
        ``\\setcounter`` line.
    """
    segs = split_into_segments(lines)
    # Precompute, for each segment, the original index of its first content line.
    orig_index: list[list[int]] = []
    cursor = 0
    for i, seg in enumerate(segs):
        if i > 0:
            cursor += 1  # the \tfsegment marker line consumed at this boundary
        idxs = list(range(cursor, cursor + len(seg.lines)))
        orig_index.append(idxs)
        cursor += len(seg.lines)

    # Absolute starting line number of each segment: numbered lines in all
    # preceding segments of the full input.
    start_line: list[int] = []
    running = 0
    for seg in segs:
        start_line.append(running)
        running += _count_numbered_lines(seg.lines)

    new_lines: list[str] = []
    idx_map: list[int] = []

    def emit_setcounter(i: int) -> None:
        if line_counter is not None:
            new_lines.append(f"\\setcounter{{{line_counter}}}{{{start_line[i]}}}")
            idx_map.append(-1)

    def emit_lines(seg_lines: list[str], idxs: list[int]) -> None:
        for ln, oi in zip(seg_lines, idxs):
            new_lines.append(ln)
            idx_map.append(oi)

    outer_env = _outer_open_env(segs[0].lines) if segs else None

    last = len(segs) - 1
    for i, seg in enumerate(segs):
        if i == last and last != 0:
            # Final segment: keep its trailing \end{<outer_env>} closer no
            # matter what (environment balance), but crop the leading content
            # like any interior segment.
            content, closer = _split_trailing_closer(seg.lines, outer_env)
            if not closer or not content:
                # No separable closer, or nothing but a closer: keep verbatim.
                emit_setcounter(i)
                emit_lines(seg.lines, orig_index[i])
                continue
            content_idx = orig_index[i][: len(content)]
            closer_idx = orig_index[i][len(content) :]
            if i in active:
                emit_setcounter(i)
                emit_lines(content, content_idx)
            else:
                new_lines.append(f"{stub_macro}{{{seg.caption or ''}}}")
                idx_map.append(-1)
            emit_lines(closer, closer_idx)
            continue

        keep = (i == 0) or (i in active)
        if keep:
            if i > 0:
                emit_setcounter(i)
            emit_lines(seg.lines, orig_index[i])
        else:
            new_lines.append(f"{stub_macro}{{{seg.caption or ''}}}")
            idx_map.append(-1)
    return new_lines, idx_map
