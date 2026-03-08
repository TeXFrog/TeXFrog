"""Tests for texfrog.filter."""

from __future__ import annotations

from texfrog.filter import (
    compute_changed_lines,
    compute_removed_lines,
    wrap_changed_line,
)


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
    line = r"		$c \gets \mathrm{Enc}(k, m)$"
    result = wrap_changed_line(line)
    assert result == r"\tfchanged{		$c \gets \mathrm{Enc}(k, m)$}"


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
    line = r"		$c \gets \mathrm{Enc}(k, m)$%"
    result = wrap_changed_line(line)
    assert result == r"\tfchanged{		$c \gets \mathrm{Enc}(k, m)$}%"


def test_wrap_trailing_percent_with_whitespace():
    r"""Trailing % with surrounding whitespace."""
    line = r"		$c \gets \mathrm{Enc}(k, m)$%  "
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


# ---------------------------------------------------------------------------
# wrap_changed_line — procedure_header_cmd (nicodemus-style headers)
# ---------------------------------------------------------------------------

def test_wrap_skip_nicodemusheader():
    r"""\nicodemusheader{...} lines are skipped when procedure_header_cmd is set."""
    line = r"		\nicodemusheader{Oracle $\Oinit(\pk)$}"
    result = wrap_changed_line(line, procedure_header_cmd="nicodemusheader")
    assert result == line


def test_wrap_skip_nicodemusheader_with_tag():
    r"""\nicodemusheader with trailing content after } is still matched."""
    line = r"		\nicodemusheader{Games $\game^b_0$-$\game^b_3$}"
    result = wrap_changed_line(line, procedure_header_cmd="nicodemusheader")
    assert result == line


def test_wrap_nicodemusheader_without_cmd_still_wraps():
    r"""Without procedure_header_cmd, \nicodemusheader lines are wrapped normally."""
    line = r"		\nicodemusheader{Oracle $\Oinit(\pk)$}"
    result = wrap_changed_line(line)
    assert result == r"\tfchanged{		\nicodemusheader{Oracle $\Oinit(\pk)$}}"


def test_wrap_item_not_affected_by_header_cmd():
    r"""\item lines still wrap normally even when procedure_header_cmd is set."""
    line = r"			\item $x\getsr\Zp$"
    result = wrap_changed_line(line, procedure_header_cmd="nicodemusheader")
    assert result.startswith("\t\t\t\\item ")
    assert r"\tfchanged{$x\getsr\Zp$}" in result
