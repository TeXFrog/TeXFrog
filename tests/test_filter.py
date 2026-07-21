"""Tests for texfrog.filter."""

from __future__ import annotations

from texfrog.filter import (
    Segment,
    compute_active_segments,
    compute_changed_lines,
    compute_removed_lines,
    crop_to_active_segments,
    split_into_segments,
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
    line = r"    $x \gets 1$"
    result = wrap_changed_line(line, macro=r"\myhl")
    assert result == r"\myhl{    $x \gets 1$}"


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
# wrap_changed_line — \State prefix (algorithmicx-style, e.g. algpseudocodex)
# ---------------------------------------------------------------------------

def test_wrap_state_prefix_stays_outside():
    r"""The \State prefix must be placed outside \tfchanged{}."""
    line = r"    \State $x \gets 1$"
    result = wrap_changed_line(line)
    assert result.startswith("    \\State ")
    assert r"\tfchanged{$x \gets 1$}" in result


def test_wrap_no_state_prefix_unchanged():
    r"""Non-\State lines are unaffected by \State handling."""
    line = r"    $c \gets \mathrm{Enc}(k, m)$"
    result = wrap_changed_line(line)
    assert result == r"\tfchanged{    $c \gets \mathrm{Enc}(k, m)$}"


def test_wrap_state_custom_macro():
    r"""Custom macro with \State prefix."""
    line = r"    \State $k \gets 1$"
    result = wrap_changed_line(line, macro=r"\tfremoved")
    assert result.startswith("    \\State ")
    assert r"\tfremoved{$k \gets 1$}" in result


def test_wrap_state_with_trailing_backslash():
    r"""\State with trailing \\ — both handled correctly."""
    line = r"    \State $x \gets 1$ \\"
    result = wrap_changed_line(line)
    assert result.startswith("    \\State ")
    assert result.endswith("\\\\")
    assert r"\tfchanged{$x \gets 1$}" in result


def test_wrap_statex_not_misparsed_as_state():
    r"""\Statex (unnumbered continuation line) is a distinct command from
    \State and must not be split into \State + a stray "x ..." suffix.
    It has no dedicated prefix handling, so the whole line is wrapped,
    same as any other unrecognized command.
    """
    line = r"    \Statex continuation text"
    result = wrap_changed_line(line)
    assert result == "\\tfchanged{    \\Statex continuation text}"


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


# ---------------------------------------------------------------------------
# split_into_segments
# ---------------------------------------------------------------------------

def test_split_into_segments_basic():
    lines = [
        r"\State a",
        r"\tfsegment{Responder}",
        r"\State b",
        r"\State c",
    ]
    segs = split_into_segments(lines)
    assert segs == [
        Segment(caption=None, lines=[r"\State a"]),
        Segment(caption="Responder", lines=[r"\State b", r"\State c"]),
    ]


def test_split_into_segments_no_markers():
    lines = [r"\State a", r"\State b"]
    segs = split_into_segments(lines)
    assert segs == [Segment(caption=None, lines=[r"\State a", r"\State b"])]


def test_split_into_segments_leading_marker():
    lines = [r"\tfsegment{First}", r"\State a"]
    segs = split_into_segments(lines)
    assert segs == [
        Segment(caption=None, lines=[]),
        Segment(caption="First", lines=[r"\State a"]),
    ]


# ---------------------------------------------------------------------------
# compute_active_segments / crop_to_active_segments
# ---------------------------------------------------------------------------

def test_compute_active_segments_detects_change():
    target = [r"\State a", r"\tfsegment{R}", r"\State b"]
    curr = [r"\State a", r"\tfsegment{R}", r"\State b2"]
    assert compute_active_segments(target, curr) == {1}


def test_compute_active_segments_none_changed():
    lines = [r"\State a", r"\tfsegment{R}", r"\State b"]
    assert compute_active_segments(lines, lines) == set()


def test_crop_keeps_active_and_stubs_inactive():
    lines = [
        r"\begin{algorithmic}",
        r"\tfsegment{Init}",
        r"\State a",
        r"\tfsegment{Resp}",
        r"\State b",
        r"\end{algorithmic}",
    ]
    # active segments: 0 (preamble, always kept) and 2 (Resp)
    new_lines, idx_map = crop_to_active_segments(lines, active={2})
    assert new_lines == [
        r"\begin{algorithmic}",
        r"\tfsegmentstub{Init}",
        r"\State b",
        r"\end{algorithmic}",
    ]
    # stub line maps to -1; kept lines map to their original indices
    assert idx_map == [0, -1, 4, 5]


def test_crop_final_segment_content_stubs_but_closer_survives():
    """The final segment's leading content crops like any interior segment,
    while its trailing ``\\end{...}`` closer is always kept for environment
    balance.

    Segment 0 (preamble, holding ``\\begin{...}``) is kept verbatim. The final
    ``Resp`` segment carries real content (``\\State b``) ahead of its
    ``\\end{algorithmic}`` closer: when it is inactive the content collapses to
    a stub but ``\\end{algorithmic}`` must survive. (Earlier the whole final
    segment was force-kept, so unchanged final-segment content — e.g. a
    responder's KEYMAT step — printed on every hop instead of cropping.)
    """
    lines = [
        r"\begin{algorithmic}",
        r"\tfsegment{Init}",
        r"\State a",
        r"\tfsegment{Resp}",
        r"\State b",
        r"\end{algorithmic}",
    ]
    # No segments active: Init (interior) stubs; Resp (final) content stubs too,
    # but \end{algorithmic} is kept.
    new_lines, idx_map = crop_to_active_segments(lines, active=set())
    assert new_lines == [
        r"\begin{algorithmic}",
        r"\tfsegmentstub{Init}",
        r"\tfsegmentstub{Resp}",
        r"\end{algorithmic}",
    ]
    assert idx_map == [0, -1, -1, 5]


def test_crop_final_segment_content_kept_when_active():
    """When the final segment is active, its content is kept (with the closer
    still following)."""
    lines = [
        r"\begin{algorithmic}",
        r"\tfsegment{Init}",
        r"\State a",
        r"\tfsegment{Resp}",
        r"\State b",
        r"\end{algorithmic}",
    ]
    # Resp (final, index 2) active -> content kept, closer kept; Init stubs.
    new_lines, idx_map = crop_to_active_segments(lines, active={2})
    assert new_lines == [
        r"\begin{algorithmic}",
        r"\tfsegmentstub{Init}",
        r"\State b",
        r"\end{algorithmic}",
    ]
    assert idx_map == [0, -1, 4, 5]


def test_crop_final_segment_inner_end_not_mistaken_for_closer():
    """An ``\\end{align}`` inside the final segment's content must not be
    peeled as the environment closer: only ``\\end{<outer env>}`` (here
    ``algorithmic``, opened in segment 0) is the closer."""
    lines = [
        r"\begin{algorithmic}",
        r"\tfsegment{Init}",
        r"\State a",
        r"\tfsegment{Resp}",
        r"\State \begin{align} x &= y \end{align}",
        r"\end{algorithmic}",
    ]
    # Resp (final) inactive: its content — including the balanced align block —
    # collapses to a single stub; only \end{algorithmic} survives.
    new_lines, _ = crop_to_active_segments(lines, active=set())
    assert new_lines == [
        r"\begin{algorithmic}",
        r"\tfsegmentstub{Init}",
        r"\tfsegmentstub{Resp}",
        r"\end{algorithmic}",
    ]


def test_crop_final_segment_closer_only_kept_verbatim():
    """A final segment that is nothing but the ``\\end{...}`` closer is kept
    verbatim (no spurious stub), whether or not it is active."""
    lines = [
        r"\begin{algorithmic}",
        r"\tfsegment{Init}",
        r"\State a",
        r"\tfsegment{End}",
        r"\end{algorithmic}",
    ]
    new_lines, idx_map = crop_to_active_segments(lines, active=set())
    assert new_lines == [
        r"\begin{algorithmic}",
        r"\tfsegmentstub{Init}",
        r"\end{algorithmic}",
    ]
    assert idx_map == [0, -1, 4]


def test_crop_stubs_each_interior_segment_on_its_own_line():
    """Each strictly-interior inactive segment gets its own stub line
    (no coalescing of a run into one comma-joined stub); the final segment's
    content stubs too, but its ``\\end{...}`` closer survives."""
    lines = [
        r"\begin{algorithmic}",
        r"\tfsegment{A}",
        r"\State a",
        r"\tfsegment{B}",
        r"\State b",
        r"\tfsegment{C}",
        r"\State c",
        r"\tfsegment{D}",
        r"\State d",
        r"\end{algorithmic}",
    ]
    # segments: 0=preamble, 1=A (active), 2=B (inactive), 3=C (inactive),
    # 4=D (last, inactive). B and C are strictly interior -> one stub each. D
    # is the final segment: its content (\State d) stubs, \end{algorithmic}
    # is kept.
    new_lines, idx_map = crop_to_active_segments(lines, active={1})
    assert new_lines == [
        r"\begin{algorithmic}",
        r"\State a",
        r"\tfsegmentstub{B}",
        r"\tfsegmentstub{C}",
        r"\tfsegmentstub{D}",
        r"\end{algorithmic}",
    ]
    assert idx_map == [0, 2, -1, -1, -1, 9]


def test_crop_injects_absolute_line_counter_resets():
    """With ``line_counter`` set, a \\setcounter is inserted before each kept
    segment after segment 0, holding the count of numbered lines in all
    preceding segments of the full input (so kept lines keep absolute
    numbers, jumping across stubs)."""
    lines = [
        r"\begin{algorithmic}[1]",
        r"\tfsegment{Alpha}",
        r"\State a1",
        r"\State a2",
        r"\tfsegment{Beta}",
        r"\State b1",
        r"\State b2",
        r"\tfsegment{Gamma}",
        r"\State g",
        r"\end{algorithmic}",
    ]
    # Full numbering: a1=1 a2=2 b1=3 b2=4 g=5. Keep seg0 + final (Gamma, whose
    # content is active here); Alpha and Beta stubbed. Gamma (index 3) starts
    # after 4 numbered lines, so its \State g must resume at absolute line 5
    # -> \setcounter{..}{4}.
    new_lines, idx_map = crop_to_active_segments(
        lines, active={3}, line_counter="ALG@line",
    )
    assert new_lines == [
        r"\begin{algorithmic}[1]",
        r"\tfsegmentstub{Alpha}",
        r"\tfsegmentstub{Beta}",
        r"\setcounter{ALG@line}{4}",
        r"\State g",
        r"\end{algorithmic}",
    ]
    # The \setcounter line is synthetic (idx_map -1), like the stubs.
    assert idx_map == [0, -1, -1, -1, 8, 9]


def test_crop_line_counter_reset_for_active_interior_segment():
    """A kept interior (active) segment also gets a \\setcounter reset to its
    absolute start, not just the final segment."""
    lines = [
        r"\begin{algorithmic}[1]",
        r"\tfsegment{Alpha}",
        r"\State a1",
        r"\State a2",
        r"\tfsegment{Beta}",
        r"\State b",
        r"\tfsegment{Gamma}",
        r"\State g",
        r"\end{algorithmic}",
    ]
    # Keep Beta (active, index 2). Alpha stubbed. Beta starts after 2
    # numbered lines (a1,a2) -> \setcounter{ALG@line}{2}; its \State b is
    # absolute line 3.
    new_lines, _ = crop_to_active_segments(
        lines, active={2}, line_counter="ALG@line",
    )
    assert r"\setcounter{ALG@line}{2}" in new_lines
    # No reset is emitted for segment 0.
    assert new_lines[0] == r"\begin{algorithmic}[1]"
    assert new_lines[1] != r"\setcounter{ALG@line}{0}"


def test_crop_no_line_counter_by_default():
    """Without ``line_counter``, no \\setcounter lines are injected."""
    lines = [
        r"\begin{algorithmic}[1]",
        r"\tfsegment{Alpha}",
        r"\State a",
        r"\tfsegment{Beta}",
        r"\State b",
        r"\end{algorithmic}",
    ]
    new_lines, _ = crop_to_active_segments(lines, active=set())
    assert not any("setcounter" in ln for ln in new_lines)
