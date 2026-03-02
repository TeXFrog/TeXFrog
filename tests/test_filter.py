"""Tests for texfrog.filter."""

from __future__ import annotations

from texfrog.filter import (
    compute_changed_lines,
    compute_removed_lines,
    filter_for_game,
    wrap_changed_line,
)
from texfrog.model import SourceLine


def make_line(content: str, tags=None) -> SourceLine:
    """Helper to construct a SourceLine for testing."""
    if tags is not None:
        tags = frozenset(tags)
    return SourceLine(content=content, tags=tags, original=content)


# ---------------------------------------------------------------------------
# filter_for_game
# ---------------------------------------------------------------------------

def test_untagged_line_appears_in_all_games():
    # An untagged line should appear in every game.
    # (The trailing \\ is stripped from the last line — that's correct behaviour.)
    content = r"    (\pk, \sk) \getsr \KEM.\keygen() \\"
    lines = [make_line(content)]
    assert filter_for_game(lines, "G0") != []
    assert filter_for_game(lines, "G1") != []
    # Content (minus trailing \\) should be present
    assert r"\KEM.\keygen()" in filter_for_game(lines, "G0")[0]


def test_tagged_line_excluded_for_other_game():
    lines = [
        make_line(r"    \key \gets F(\key_A) \\", tags={"G0", "G1"}),
    ]
    assert filter_for_game(lines, "G2") == []


def test_tagged_line_included_for_own_game():
    lines = [
        make_line(r"    \key \gets F(\key_A) \\", tags={"G0", "G1"}),
    ]
    result = filter_for_game(lines, "G0")
    assert len(result) == 1
    assert r"\key \gets F(\key_A)" in result[0]


def test_only_matching_lines_included():
    lines = [
        make_line(r"    common \\"),                          # untagged
        make_line(r"    only_g0 \\", tags={"G0"}),           # G0 only
        make_line(r"    only_g1 \\", tags={"G1"}),           # G1 only
        make_line(r"    also_common \\"),                    # untagged
    ]
    g0 = filter_for_game(lines, "G0")
    assert any("only_g0" in l for l in g0)
    assert not any("only_g1" in l for l in g0)
    assert any("common" in l for l in g0)

    g1 = filter_for_game(lines, "G1")
    assert any("only_g1" in l for l in g1)
    assert not any("only_g0" in l for l in g1)


def test_trailing_backslash_stripped_from_last_line():
    lines = [
        make_line(r"    line1 \\"),
        make_line(r"    line2 \\"),   # this becomes the last included line
    ]
    result = filter_for_game(lines, "G0")
    assert result[-1].rstrip().endswith("line2")
    assert not result[-1].rstrip().endswith("\\\\")


def test_trailing_backslash_not_stripped_from_intermediate_lines():
    lines = [
        make_line(r"    line1 \\"),
        make_line(r"    line2 \\"),
        make_line(r"    line3"),    # last line has no \\
    ]
    result = filter_for_game(lines, "G0")
    assert result[0].rstrip().endswith("\\\\")
    assert result[1].rstrip().endswith("\\\\")
    assert result[2].rstrip() == "    line3"


def test_no_trailing_backslash_on_non_cryptocode_style():
    """algorithmicx-style lines don't end with \\; nothing should be stripped."""
    lines = [
        make_line(r"    \State $x \gets 1$"),
        make_line(r"    \State $y \gets 2$"),
    ]
    result = filter_for_game(lines, "G0")
    assert result == [r"    \State $x \gets 1$", r"    \State $y \gets 2$"]


def test_empty_lines_at_end_not_confused_for_last_content_line():
    lines = [
        make_line(r"    content \\"),
        make_line(""),               # trailing blank line (untagged)
    ]
    result = filter_for_game(lines, "G0")
    # Trailing \\ should be stripped from "content" line (last non-empty)
    content_line = next(l for l in result if l.strip())
    assert not content_line.rstrip().endswith("\\\\")


# ---------------------------------------------------------------------------
# compute_changed_lines
# ---------------------------------------------------------------------------

def test_no_changes_when_equal():
    lines = ["a \\\\", "b \\\\", "c"]
    assert compute_changed_lines(lines, lines) == set()


def test_first_game_no_changes():
    curr = ["a \\\\", "b"]
    assert compute_changed_lines([], curr) == set()


def test_added_line_detected():
    prev = ["a \\\\", "c"]
    curr = ["a \\\\", "b \\\\", "c"]  # "b" is new
    changed = compute_changed_lines(prev, curr)
    assert 1 in changed   # index of "b \\\\"
    assert 0 not in changed
    assert 2 not in changed


def test_replaced_line_detected():
    prev = ["a \\\\", "old \\\\", "c"]
    curr = ["a \\\\", "new \\\\", "c"]  # "old" replaced by "new"
    changed = compute_changed_lines(prev, curr)
    assert 1 in changed
    assert 0 not in changed
    assert 2 not in changed


def test_unchanged_lines_not_flagged():
    prev = ["a \\\\", "b \\\\", "c"]
    curr = ["a \\\\", "b \\\\", "c", "d"]  # "d" added at end
    changed = compute_changed_lines(prev, curr)
    assert 3 in changed
    assert 0 not in changed
    assert 1 not in changed
    assert 2 not in changed


# ---------------------------------------------------------------------------
# compute_removed_lines
# ---------------------------------------------------------------------------

def test_no_removals_when_equal():
    lines = ["a \\\\", "b \\\\", "c"]
    assert compute_removed_lines(lines, lines) == set()


def test_no_removals_from_empty_prev():
    curr = ["a \\\\", "b"]
    assert compute_removed_lines([], curr) == set()


def test_deleted_line_detected():
    prev = ["a \\\\", "b \\\\", "c"]
    curr = ["a \\\\", "c"]  # "b" deleted
    removed = compute_removed_lines(prev, curr)
    assert 1 in removed   # index of "b \\\\" in prev
    assert 0 not in removed
    assert 2 not in removed


def test_replaced_line_detected_in_prev():
    prev = ["a \\\\", "old \\\\", "c"]
    curr = ["a \\\\", "new \\\\", "c"]  # "old" replaced by "new"
    removed = compute_removed_lines(prev, curr)
    assert 1 in removed   # "old" in prev is being replaced
    assert 0 not in removed
    assert 2 not in removed


def test_no_removals_when_only_additions():
    prev = ["a \\\\", "b \\\\", "c"]
    curr = ["a \\\\", "b \\\\", "c", "d"]  # "d" added, nothing removed
    removed = compute_removed_lines(prev, curr)
    assert removed == set()


def test_removed_and_changed_symmetric_on_replace():
    prev = ["a \\\\", "old \\\\", "c"]
    curr = ["a \\\\", "new \\\\", "c"]
    removed = compute_removed_lines(prev, curr)
    changed = compute_changed_lines(prev, curr)
    # Both should flag index 1 in their respective lists
    assert 1 in removed
    assert 1 in changed


# ---------------------------------------------------------------------------
# wrap_changed_line
# ---------------------------------------------------------------------------

def test_wrap_line_with_trailing_backslash():
    line = r"    \key \gets F(\key_A) \\"
    result = wrap_changed_line(line)
    # Trailing space inside \key_A is stripped; \\ placed outside with a space.
    assert result == r"\tfchanged{    \key \gets F(\key_A)} \\"


def test_wrap_line_without_trailing_backslash():
    line = r"    \pcreturn \adv(\pk)"
    result = wrap_changed_line(line)
    assert result == r"\tfchanged{    \pcreturn \adv(\pk)}"


def test_wrap_custom_macro():
    line = r"    \State $x \gets 1$"
    result = wrap_changed_line(line, macro=r"\myhl")
    assert result == r"\myhl{    \State $x \gets 1$}"


def test_wrap_line_with_backslash_and_trailing_space():
    line = r"    \key \gets F(\key_A) \\  "
    result = wrap_changed_line(line)
    # The \\ should still be placed outside
    assert result.endswith("\\\\")
    assert r"\tfchanged{" in result


# ---------------------------------------------------------------------------
# wrap_changed_line — \item prefix (nicodemus-style)
# ---------------------------------------------------------------------------

def test_wrap_item_prefix_stays_outside():
    r"""The \item prefix must be placed outside \tfchanged{}."""
    line = r"			\item $x\getsr\Zp$"
    result = wrap_changed_line(line)
    assert result.startswith("\t\t\t\\item ")
    assert r"\tfchanged{$x\getsr\Zp$}" in result


def test_wrap_item_with_indentation():
    r"""Indented \item (e.g. \quad) preserves structure."""
    line = r"			\item \quad $P[n]\gets j$"
    result = wrap_changed_line(line)
    assert result.startswith("\t\t\t\\item ")
    assert r"\tfchanged{\quad $P[n]\gets j$}" in result


def test_wrap_item_custom_macro():
    r"""Custom macro with \item prefix."""
    line = r"			\item $k\getsr\ksp$"
    result = wrap_changed_line(line, macro=r"\tfremoved")
    assert r"\tfremoved{$k\getsr\ksp$}" in result
    assert result.startswith("\t\t\t\\item ")


def test_wrap_no_item_prefix_unchanged():
    r"""Non-\item lines are unaffected by \item handling."""
    line = r"		\textbf{Oracle} $\Oinit(\pk)$"
    result = wrap_changed_line(line)
    assert result == r"\tfchanged{		\textbf{Oracle} $\Oinit(\pk)$}"


def test_wrap_item_with_trailing_backslash():
    r"""\item with trailing \\ — both handled correctly."""
    line = r"			\item $x\gets 1$ \\"
    result = wrap_changed_line(line)
    assert result.startswith("\t\t\t\\item ")
    assert result.endswith("\\\\")
    assert r"\tfchanged{$x\gets 1$}" in result


# ---------------------------------------------------------------------------
# wrap_changed_line — trailing % (LaTeX newline suppressor)
# ---------------------------------------------------------------------------

def test_wrap_trailing_percent_moved_outside():
    r"""Trailing % must be placed outside \tfchanged{} to avoid commenting out }."""
    line = r"		\textbf{Oracle} $\Oexp(i)$%"
    result = wrap_changed_line(line)
    assert result == r"\tfchanged{		\textbf{Oracle} $\Oexp(i)$}%"


def test_wrap_trailing_percent_with_whitespace():
    r"""Trailing % with surrounding whitespace."""
    line = r"		\textbf{Oracle} $\Oexp(i)$%  "
    result = wrap_changed_line(line)
    assert result.endswith("%")
    assert r"\tfchanged{" in result


def test_wrap_trailing_percent_with_item():
    r"""\item prefix + trailing % — both handled correctly."""
    line = r"			\item $content$%"
    result = wrap_changed_line(line)
    assert result.startswith("\t\t\t\\item ")
    assert result.endswith("%")
    assert r"\tfchanged{$content$}" in result


def test_wrap_escaped_percent_not_extracted():
    r"""A \% (escaped percent) is content, not a newline suppressor."""
    line = r"    $x = 10\%$"
    result = wrap_changed_line(line)
    # The \% is content — should stay inside the macro
    assert result == r"\tfchanged{    $x = 10\%$}"


def test_wrap_trailing_backslash_takes_priority_over_percent():
    r"""If line has both \\ and %, the \\ wins (it appears last in cryptocode)."""
    line = r"    content \\"
    result = wrap_changed_line(line)
    assert result.endswith("\\\\")
    assert r"\tfchanged{    content}" in result


# ---------------------------------------------------------------------------
# wrap_changed_line — structural line guards
# ---------------------------------------------------------------------------

def test_wrap_skip_markersetlen():
    r"""\markersetlen lines are layout-only and should not be wrapped."""
    line = r"\markersetlen{ndR}{195pt}%"
    assert wrap_changed_line(line) == line


def test_wrap_skip_markersetlen_with_indent():
    r"""Indented \markersetlen also skipped."""
    line = r"	\markersetlen{ndL}{170pt}%"
    assert wrap_changed_line(line) == line


def test_wrap_skip_brace_percent():
    r"""Lines ending with {%% are structural openers (e.g. \nicodemusbox{...}{%)."""
    line = r"	\nicodemusbox{\markerlenndL}{%"
    assert wrap_changed_line(line) == line


def test_wrap_skip_begin_environment():
    r"""\begin{...} lines are environment boundaries, not wrappable content."""
    line = r"		\begin{nicodemus}"
    assert wrap_changed_line(line) == line


def test_wrap_skip_end_environment():
    r"""\end{...} lines are environment boundaries."""
    line = r"		\end{nicodemus}%"
    assert wrap_changed_line(line) == line
