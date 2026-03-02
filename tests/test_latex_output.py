"""Tests for texfrog.output.latex."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.model import Figure, Game, Proof, SourceLine
from texfrog.output.html import _expand_tfgamename
from texfrog.output.latex import (
    _replace_proc_header_title,
    _write_game_file,
    generate_latex,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "simple"


def make_proof() -> Proof:
    """Build a small synthetic Proof for output tests."""
    games = [
        Game(label="G0", latex_name=r"\REAL()", description="Starting game."),
        Game(label="G1", latex_name="G_1", description="Modified game."),
        Game(label="G2", latex_name="G_2", description="Final game."),
    ]
    source_lines = [
        SourceLine(r"\begin{procedure}", None, r"\begin{procedure}"),
        SourceLine(r"    common \\", None, r"    common \\"),
        SourceLine(r"    only_g0 \\", frozenset({"G0"}), r"    only_g0 \\ %:tags: G0"),
        SourceLine(r"    only_g1 \\", frozenset({"G1", "G2"}), r"    only_g1 \\ %:tags: G1,G2"),
        SourceLine(r"    \pcreturn \adv", None, r"    \pcreturn \adv"),
        SourceLine(r"\end{procedure}", None, r"\end{procedure}"),
    ]
    commentary = {
        "G0": "This is the G0 commentary.\n",
        "G1": r"\begin{claim}G0 and G1 are equiv.\end{claim}" + "\n",
    }
    figures = [
        Figure(label="start_end", games=["G0", "G2"]),
    ]
    return Proof(
        macros=["macros.tex"],
        games=games,
        source_lines=source_lines,
        commentary=commentary,
        figures=figures,
    )


# ---------------------------------------------------------------------------
# Per-game files
# ---------------------------------------------------------------------------

def test_game_files_created(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    assert (tmp_path / "G0.tex").exists()
    assert (tmp_path / "G1.tex").exists()
    assert (tmp_path / "G2.tex").exists()


def test_first_game_no_tfchanged(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "G0.tex").read_text()
    assert r"\tfchanged" not in text


def test_changed_line_wrapped_in_g1(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "G1.tex").read_text()
    # "only_g1" replaces "only_g0" — should be wrapped
    assert r"\tfchanged" in text
    assert "only_g1" in text


def test_unchanged_line_not_wrapped(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "G1.tex").read_text()
    # "common" is unchanged; it should appear unwrapped
    assert "common" in text
    # The common line should not be inside \tfchanged
    lines_with_common = [l for l in text.splitlines() if "common" in l]
    for l in lines_with_common:
        assert r"\tfchanged" not in l


def test_write_game_file_custom_macro(tmp_path):
    """_write_game_file should use the provided macro for wrapping."""
    lines = [r"    common \\", r"    changed \\", r"    end"]
    _write_game_file("test", lines, {1}, tmp_path / "test.tex", macro=r"\tfremoved")
    text = (tmp_path / "test.tex").read_text()
    assert r"\tfremoved" in text
    assert r"\tfchanged" not in text
    assert "changed" in text


def test_excluded_line_not_in_game_file(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    g0_text = (tmp_path / "G0.tex").read_text()
    assert "only_g0" in g0_text
    assert "only_g1" not in g0_text

    g1_text = (tmp_path / "G1.tex").read_text()
    assert "only_g1" in g1_text
    assert "only_g0" not in g1_text


# ---------------------------------------------------------------------------
# Commentary files
# ---------------------------------------------------------------------------

def test_commentary_file_created(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    assert (tmp_path / "G0_commentary.tex").exists()
    assert (tmp_path / "G1_commentary.tex").exists()


def test_commentary_file_content(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "G0_commentary.tex").read_text()
    assert "G0 commentary" in text


def test_no_commentary_file_when_empty(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    # G2 has no commentary in our fixture
    assert not (tmp_path / "G2_commentary.tex").exists()


# ---------------------------------------------------------------------------
# Harness file
# ---------------------------------------------------------------------------

def test_harness_file_created(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    assert (tmp_path / "proof_harness.tex").exists()


def test_sty_file_created(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    assert (tmp_path / "texfrog.sty").exists()


def test_harness_inputs_all_games(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    assert r"\input{G0.tex}" in text
    assert r"\input{G1.tex}" in text
    assert r"\input{G2.tex}" in text


def test_harness_inputs_commentaries(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    assert r"\input{G0_commentary.tex}" in text
    assert r"\input{G1_commentary.tex}" in text


def test_harness_does_not_input_macros(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    assert r"\input{macros.tex}" not in text


def test_sty_defines_tfchanged(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "texfrog.sty").read_text()
    assert r"\tfchanged" in text


def test_harness_games_in_order(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    pos_g0 = text.index("G0.tex")
    pos_g1 = text.index("G1.tex")
    pos_g2 = text.index("G2.tex")
    assert pos_g0 < pos_g1 < pos_g2


# ---------------------------------------------------------------------------
# Consolidated figures
# ---------------------------------------------------------------------------

def test_consolidated_figure_created(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    assert (tmp_path / "fig_start_end.tex").exists()


def test_consolidated_common_line_no_annotation(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_start_end.tex").read_text()
    # "common" is in all games — should appear without \tfgamelabel
    lines_with_common = [l for l in text.splitlines() if "common" in l]
    assert lines_with_common
    for l in lines_with_common:
        assert r"\tfgamelabel" not in l


def test_consolidated_subset_line_annotated(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_start_end.tex").read_text()
    # "only_g0" appears in G0 but not G2 — should have \tfgamelabel
    lines_with_only_g0 = [l for l in text.splitlines() if "only_g0" in l]
    assert lines_with_only_g0
    assert any(r"\tfgamelabel" in l for l in lines_with_only_g0)


def test_consolidated_line_only_in_missing_game_skipped(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_start_end.tex").read_text()
    # "only_g1" is tagged for G1 and G2; figure is G0,G2; so only_g1 appears for G2
    # It should still be included (annotated with G2)
    assert "only_g1" in text


# ---------------------------------------------------------------------------
# Consolidated figures — LaTeX correctness
# ---------------------------------------------------------------------------


def _make_figure_proof(source_lines, game_labels):
    """Build a minimal Proof with one consolidated figure over the given games."""
    games = [Game(label=lbl, latex_name=lbl, description="") for lbl in game_labels]
    return Proof(
        macros=[],
        games=games,
        source_lines=source_lines,
        commentary={},
        figures=[Figure(label="main", games=list(game_labels))],
    )


def test_consolidated_proc_headers_collapse_to_one(tmp_path):
    """Game-specific \\procedure headers in a slot must collapse to a single line."""
    source_lines = [
        SourceLine(r"    \procedure{G0 title}{", frozenset({"G0"}), ""),
        SourceLine(r"    \procedure{G1 title}{", frozenset({"G1"}), ""),
        SourceLine(r"        body \\", None, ""),
        SourceLine(r"    }", None, ""),
    ]
    proof = _make_figure_proof(source_lines, ["G0", "G1"])
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    proc_lines = [l for l in text.splitlines() if r"\procedure" in l]
    assert len(proc_lines) == 1


def test_consolidated_proc_header_not_annotated(tmp_path):
    """A game-specific \\procedure header must not be wrapped in \\tfgamelabel."""
    source_lines = [
        SourceLine(r"    \procedure{G0 title}{", frozenset({"G0"}), ""),
        SourceLine(r"    \procedure{G1 title}{", frozenset({"G1"}), ""),
        SourceLine(r"        body \\", None, ""),
        SourceLine(r"    }", None, ""),
    ]
    proof = _make_figure_proof(source_lines, ["G0", "G1"])
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    proc_lines = [l for l in text.splitlines() if r"\procedure" in l]
    assert proc_lines
    assert r"\tfgamelabel" not in proc_lines[0]


def test_consolidated_blank_lines_skipped(tmp_path):
    """Blank source lines must not appear in the consolidated figure output."""
    source_lines = [
        SourceLine(r"    body \\", None, ""),
        SourceLine("", None, ""),  # blank
        SourceLine(r"    end", None, ""),
    ]
    proof = _make_figure_proof(source_lines, ["G0", "G1"])
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    assert "\n\n" not in text


def test_consolidated_trailing_backslash_outside_macro(tmp_path):
    r"""Trailing \\ must be placed outside \tfgamelabel{}{}, not inside the braces."""
    source_lines = [
        SourceLine(r"    tagged \\", frozenset({"G0"}), ""),
        SourceLine(r"    end", None, ""),
    ]
    proof = _make_figure_proof(source_lines, ["G0", "G1"])
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    tagged_lines = [l for l in text.splitlines() if "tagged" in l]
    assert tagged_lines
    line = tagged_lines[0]
    assert r"\tfgamelabel" in line
    # \\ must appear after the closing } of \tfgamelabel's second argument
    assert r"tagged} \\" in line


# ---------------------------------------------------------------------------
# Game name macro (\tfgamename)
# ---------------------------------------------------------------------------

def test_sty_defines_tfgamename_dispatcher(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "texfrog.sty").read_text()
    assert r"\providecommand{\tfgamename}[1]{\ensuremath{\@nameuse{tfgn@#1}}}" in text


def test_sty_tfgamename_entries_for_all_games(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "texfrog.sty").read_text()
    assert r"\@namedef{tfgn@G0}{\REAL()}" in text
    assert r"\@namedef{tfgn@G1}{G_1}" in text
    assert r"\@namedef{tfgn@G2}{G_2}" in text


def test_sty_tfgamename_wrapped_in_makeatletter(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "texfrog.sty").read_text()
    start = text.index(r"\makeatletter")
    end = text.index(r"\makeatother")
    assert start < end
    assert r"\@namedef{tfgn@G0}" in text[start:end]
    assert r"\tfgamename" in text[start:end]


def test_sty_tfgamename_with_braces_in_latex_name(tmp_path):
    """Ensure latex_name values with nested braces are emitted correctly."""
    games = [
        Game(label="G0", latex_name=r"\indcca_{\QSH}^\adv.\REAL()", description="test"),
    ]
    proof = Proof(macros=[], games=games, source_lines=[], commentary={}, figures=[])
    generate_latex(proof, tmp_path)
    text = (tmp_path / "texfrog.sty").read_text()
    assert r"\@namedef{tfgn@G0}{\indcca_{\QSH}^\adv.\REAL()}" in text


# ---------------------------------------------------------------------------
# HTML game name expansion
# ---------------------------------------------------------------------------

def test_expand_tfgamename_replaces_known_labels():
    names = {"G0": r"\REAL()", "G1": "G_1"}
    text = r"In \tfgamename{G0}, we start. Then \tfgamename{G1} modifies."
    result = _expand_tfgamename(text, names)
    assert result == r"In $\REAL()$, we start. Then $G_1$ modifies."


def test_expand_tfgamename_preserves_unknown_labels():
    names = {"G0": r"\REAL()"}
    text = r"See \tfgamename{G99} for details."
    result = _expand_tfgamename(text, names)
    assert result == r"See \tfgamename{G99} for details."


def test_expand_tfgamename_no_op_without_macro():
    names = {"G0": r"\REAL()"}
    text = "No macro references here."
    result = _expand_tfgamename(text, names)
    assert result == text


def test_expand_tfgamename_inside_dollar_math():
    r"""Don't double-wrap when \tfgamename is already inside $...$."""
    names = {"G0": "G_0"}
    text = r"The starting game is $\tfgamename{G0} = \mathrm{Real}$."
    result = _expand_tfgamename(text, names)
    assert result == r"The starting game is $G_0 = \mathrm{Real}$."


def test_expand_tfgamename_mixed_math_and_text():
    """Handle both in-math and text-mode occurrences in the same string."""
    names = {"G0": "G_0", "G1": "G_1"}
    text = r"Game $\tfgamename{G0}$ equals \tfgamename{G1}."
    result = _expand_tfgamename(text, names)
    assert result == r"Game $G_0$ equals $G_1$."


def test_expand_tfgamename_inside_paren_math():
    r"""Don't double-wrap when \tfgamename is inside \(...\)."""
    names = {"G0": "G_0"}
    text = r"See \(\tfgamename{G0} = X\) for details."
    result = _expand_tfgamename(text, names)
    assert result == r"See \(G_0 = X\) for details."


def test_expand_tfgamename_inside_bracket_math():
    r"""Don't double-wrap when \tfgamename is inside \[...\]."""
    names = {"G0": "G_0"}
    text = r"Display: \[\tfgamename{G0} = X\]"
    result = _expand_tfgamename(text, names)
    assert result == r"Display: \[G_0 = X\]"


def test_expand_tfgamename_comment_with_dollar():
    r"""A $ inside a LaTeX comment should not affect math-mode tracking."""
    names = {"G0": "G_0"}
    text = "Some text % comment with a $\n\\tfgamename{G0} here."
    result = _expand_tfgamename(text, names)
    assert result == "Some text % comment with a $\n$G_0$ here."


# ---------------------------------------------------------------------------
# Consolidated figures — LaTeX correctness (continued)
# ---------------------------------------------------------------------------


def test_consolidated_last_line_variants_separator_added(tmp_path):
    r"""Variant 'last lines' with no \\ in source get \\ inserted between them."""
    source_lines = [
        SourceLine(r"    \procedure{Title}{", None, ""),
        SourceLine(r"        body \\", None, ""),
        SourceLine(r"        \pcreturn A", frozenset({"G0"}), ""),  # no \\
        SourceLine(r"        \pcreturn B", frozenset({"G1"}), ""),  # no \\
        SourceLine(r"    }", None, ""),
    ]
    proof = _make_figure_proof(source_lines, ["G0", "G1"])
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    lines = text.splitlines()

    g0_line = next((l for l in lines if "pcreturn A" in l), None)
    g1_line = next((l for l in lines if "pcreturn B" in l), None)
    assert g0_line is not None and g1_line is not None
    # G0's return is followed by more content → needs \\
    assert g0_line.rstrip().endswith("\\\\")
    # G1's return is the last before } → no \\
    assert not g1_line.rstrip().endswith("\\\\")


# ---------------------------------------------------------------------------
# Nicodemus package support
# ---------------------------------------------------------------------------


def _make_nicodemus_proof(source_lines=None, game_labels=None, figures=None):
    """Build a minimal nicodemus-package Proof."""
    if game_labels is None:
        game_labels = ["G0", "G1"]
    if source_lines is None:
        source_lines = [
            SourceLine(r"		\begin{nicodemus}", None, ""),
            SourceLine(r"			\item common line", None, ""),
            SourceLine(r"			\item $x\getsr\Zp$", frozenset({"G0"}), ""),
            SourceLine(r"			\item $x\gets\Ogen$", frozenset({"G1"}), ""),
            SourceLine(r"			\item Return $x$", None, ""),
            SourceLine(r"		\end{nicodemus}%", None, ""),
        ]
    games = [Game(label=lbl, latex_name=lbl, description="") for lbl in game_labels]
    return Proof(
        macros=[],
        games=games,
        source_lines=source_lines,
        commentary={},
        figures=figures or [],
        package="nicodemus",
    )


def test_nicodemus_sty_no_ensuremath(tmp_path):
    r"""Nicodemus texfrog.sty \tfchanged should NOT use $..$ wrapping."""
    proof = _make_nicodemus_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "texfrog.sty").read_text()
    assert r"\providecommand{\tfchanged}[1]{\colorbox{blue!15}{#1}}" in text
    assert "$#1$" not in text


def test_nicodemus_sty_no_pccomment(tmp_path):
    r"""Nicodemus texfrog.sty \tfgamelabel should NOT use \pccomment."""
    proof = _make_nicodemus_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "texfrog.sty").read_text()
    assert r"\pccomment" not in text


def test_nicodemus_sty_codecomment(tmp_path):
    r"""Nicodemus texfrog.sty should define \codecomment and use it in \tfgamelabel."""
    proof = _make_nicodemus_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "texfrog.sty").read_text()
    assert r"\providecommand{\tfniccodecomment}" in text
    assert r"\providecommand{\tfniccommentseparator}" in text
    assert r"\tfniccodecomment{#1}" in text


def test_nicodemus_game_item_prefix_outside_tfchanged(tmp_path):
    r"""\item prefix must stay outside \tfchanged in per-game output."""
    proof = _make_nicodemus_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "G1.tex").read_text()
    # G1 should have \tfchanged for the G1-only line
    assert r"\tfchanged" in text
    # \item should NOT be inside \tfchanged
    changed_lines = [l for l in text.splitlines() if r"\tfchanged" in l]
    for l in changed_lines:
        assert r"\tfchanged{\item" not in l.replace(" ", "").replace("\t", "")


def test_nicodemus_consolidated_no_backslash_insertion(tmp_path):
    r"""Nicodemus consolidated figures must NOT insert \\ between lines."""
    source_lines = [
        SourceLine(r"		\begin{nicodemus}", None, ""),
        SourceLine(r"			\item common line", None, ""),
        SourceLine(r"			\item $x\getsr\Zp$", frozenset({"G0"}), ""),
        SourceLine(r"			\item $x\gets\Ogen$", frozenset({"G1"}), ""),
        SourceLine(r"			\item Return $x$", None, ""),
        SourceLine(r"		\end{nicodemus}%", None, ""),
    ]
    proof = _make_nicodemus_proof(
        source_lines=source_lines,
        figures=[Figure(label="main", games=["G0", "G1"])],
    )
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    # No \\ should have been inserted — nicodemus uses \item, not \\
    content_lines = [l for l in text.splitlines()
                     if l.strip() and not l.strip().startswith("%")]
    for l in content_lines:
        # Lines should NOT end with \\ (nicodemus doesn't use line separators)
        assert not l.rstrip().endswith("\\\\"), f"Unexpected \\\\ in: {l}"


# ---------------------------------------------------------------------------
# Changed-line diffing skips reductions
# ---------------------------------------------------------------------------


def test_game_after_reduction_diffs_against_previous_game(tmp_path):
    """A non-reduction game should diff against the previous non-reduction game,
    not against an intervening reduction."""
    games = [
        Game(label="G0", latex_name="G_0", description=""),
        Game(label="Red", latex_name="Red", description="", reduction=True),
        Game(label="G1", latex_name="G_1", description=""),
    ]
    source_lines = [
        SourceLine(r"    common \\", None, ""),
        # same_line appears identically in G0 and G1 but NOT in Red
        SourceLine(r"    same_line \\", frozenset({"G0", "G1"}), ""),
        SourceLine(r"    red_line \\", frozenset({"Red"}), ""),
    ]
    proof = Proof(
        macros=[], games=games, source_lines=source_lines,
        commentary={}, figures=[],
    )
    generate_latex(proof, tmp_path)
    g1_text = (tmp_path / "G1.tex").read_text()
    # same_line is identical in G0 and G1, so it should NOT be highlighted
    same_lines = [l for l in g1_text.splitlines() if "same_line" in l]
    assert same_lines
    for l in same_lines:
        assert r"\tfchanged" not in l, (
            "same_line should not be marked changed when diffing G1 against G0"
        )


def test_reduction_diffs_against_immediately_preceding(tmp_path):
    """A reduction should diff against the immediately preceding entry."""
    games = [
        Game(label="G0", latex_name="G_0", description=""),
        Game(label="Red", latex_name="Red", description="", reduction=True),
    ]
    source_lines = [
        SourceLine(r"    common \\", None, ""),
        SourceLine(r"    g0_only \\", frozenset({"G0"}), ""),
        SourceLine(r"    red_only \\", frozenset({"Red"}), ""),
    ]
    proof = Proof(
        macros=[], games=games, source_lines=source_lines,
        commentary={}, figures=[],
    )
    generate_latex(proof, tmp_path)
    red_text = (tmp_path / "Red.tex").read_text()
    # red_only replaces g0_only — should be highlighted
    red_lines = [l for l in red_text.splitlines() if "red_only" in l]
    assert red_lines
    assert any(r"\tfchanged" in l for l in red_lines)


def test_nicodemus_harness_does_not_input_macros(tmp_path):
    r"""No macro files should get \input{} in the harness."""
    games = [Game(label="G0", latex_name="G_0", description="")]
    proof = Proof(
        macros=["commands.tex", "nicodemus.sty", "bpmarker.sty"],
        games=games,
        source_lines=[SourceLine(r"\item test", None, "")],
        commentary={},
        figures=[],
        package="nicodemus",
    )
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    assert r"\input{commands.tex}" not in text
    assert r"\input{nicodemus.sty}" not in text
    assert r"\input{bpmarker.sty}" not in text


# ---------------------------------------------------------------------------
# _replace_proc_header_title
# ---------------------------------------------------------------------------


def test_replace_proc_header_title_cryptocode():
    r"""Replace title in a cryptocode \procedure[opts]{TITLE}{ line."""
    line = r"    \procedure[linenumbering]{Game $G_0$}{"
    result = _replace_proc_header_title(line, r"Games $G_0$--$G_2$")
    assert result == r"    \procedure[linenumbering]{Games $G_0$--$G_2$}{"


def test_replace_proc_header_title_nested_braces():
    r"""Title with nested braces (e.g. \tfgamename{G0}) is replaced correctly."""
    line = r"    \procedure[linenumbering]{Game $\tfgamename{G0} = \REAL()$}{"
    result = _replace_proc_header_title(line, r"Games $G_0$--$G_2$")
    assert result == r"    \procedure[linenumbering]{Games $G_0$--$G_2$}{"


def test_replace_proc_header_title_nicodemus():
    r"""Replace title in a nicodemus \nicodemusheader{TITLE} line."""
    line = r"		\nicodemusheader{Games $\game^b_0$-$\game^b_3$}"
    result = _replace_proc_header_title(line, r"All games")
    assert result == r"		\nicodemusheader{All games}"


def test_replace_proc_header_title_no_options():
    r"""Procedure without optional [...] arguments."""
    line = r"    \procedure{Title}{"
    result = _replace_proc_header_title(line, "New Title")
    assert result == r"    \procedure{New Title}{"


# ---------------------------------------------------------------------------
# Consolidated figures — procedure_name
# ---------------------------------------------------------------------------


def test_consolidated_procedure_name_replaces_first_header(tmp_path):
    """procedure_name on a figure replaces the first collapsed proc header title."""
    source_lines = [
        SourceLine(r"    \procedure[linenumbering]{Game $G_0$}{", frozenset({"G0"}), ""),
        SourceLine(r"    \procedure[linenumbering]{Game $G_1$}{", frozenset({"G1"}), ""),
        SourceLine(r"        body \\", None, ""),
        SourceLine(r"    }", None, ""),
    ]
    proof = _make_figure_proof(source_lines, ["G0", "G1"])
    proof.figures[0].procedure_name = r"Games $G_0$--$G_1$"
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    proc_lines = [l for l in text.splitlines() if r"\procedure" in l]
    assert len(proc_lines) == 1
    assert r"Games $G_0$--$G_1$" in proc_lines[0]
    assert r"Game $G_0$" not in proc_lines[0]


def test_consolidated_procedure_name_only_affects_first(tmp_path):
    """procedure_name replaces only the first proc header, not subsequent ones."""
    source_lines = [
        SourceLine(r"    \procedure{Game $G_0$}{", frozenset({"G0"}), ""),
        SourceLine(r"    \procedure{Game $G_1$}{", frozenset({"G1"}), ""),
        SourceLine(r"        body \\", None, ""),
        SourceLine(r"    }", None, ""),
        SourceLine(r"    \procedure{$\mathsf{LR}(m_0, m_1)$}{", None, ""),
        SourceLine(r"        oracle body \\", None, ""),
        SourceLine(r"    }", None, ""),
    ]
    proof = _make_figure_proof(source_lines, ["G0", "G1"])
    proof.figures[0].procedure_name = "Custom Title"
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    proc_lines = [l for l in text.splitlines() if r"\procedure" in l]
    assert len(proc_lines) == 2
    assert "Custom Title" in proc_lines[0]
    # Second procedure header unchanged
    assert r"$\mathsf{LR}(m_0, m_1)$" in proc_lines[1]


def test_consolidated_no_procedure_name_preserves_original(tmp_path):
    """Without procedure_name, the first game's header is used as before."""
    source_lines = [
        SourceLine(r"    \procedure{Game $G_0$}{", frozenset({"G0"}), ""),
        SourceLine(r"    \procedure{Game $G_1$}{", frozenset({"G1"}), ""),
        SourceLine(r"        body \\", None, ""),
        SourceLine(r"    }", None, ""),
    ]
    proof = _make_figure_proof(source_lines, ["G0", "G1"])
    generate_latex(proof, tmp_path)
    text = (tmp_path / "fig_main.tex").read_text()
    proc_lines = [l for l in text.splitlines() if r"\procedure" in l]
    assert len(proc_lines) == 1
    assert r"Game $G_0$" in proc_lines[0]
