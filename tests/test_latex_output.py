"""Tests for texfrog.output.latex."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.model import Figure, Game, Proof, SourceLine
from texfrog.output.html import _expand_tfgamename
from texfrog.output.latex import _write_game_file, generate_latex

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


def test_harness_inputs_macros(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    assert r"\input{macros.tex}" in text


def test_harness_defines_tfchanged(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
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

def test_harness_defines_tfgamename_dispatcher(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    assert r"\providecommand{\tfgamename}[1]{\ensuremath{\@nameuse{tfgn@#1}}}" in text


def test_harness_tfgamename_entries_for_all_games(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    assert r"\@namedef{tfgn@G0}{\REAL()}" in text
    assert r"\@namedef{tfgn@G1}{G_1}" in text
    assert r"\@namedef{tfgn@G2}{G_2}" in text


def test_harness_tfgamename_wrapped_in_makeatletter(tmp_path):
    proof = make_proof()
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
    start = text.index(r"\makeatletter")
    end = text.index(r"\makeatother")
    assert start < end
    assert r"\@namedef{tfgn@G0}" in text[start:end]
    assert r"\tfgamename" in text[start:end]


def test_harness_tfgamename_with_braces_in_latex_name(tmp_path):
    """Ensure latex_name values with nested braces are emitted correctly."""
    games = [
        Game(label="G0", latex_name=r"\indcca_{\QSH}^\adv.\REAL()", description="test"),
    ]
    proof = Proof(macros=[], games=games, source_lines=[], commentary={}, figures=[])
    generate_latex(proof, tmp_path)
    text = (tmp_path / "proof_harness.tex").read_text()
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
