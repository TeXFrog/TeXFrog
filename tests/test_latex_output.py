"""Tests for texfrog.output.latex."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.model import Figure, Game, Proof, SourceLine
from texfrog.output.latex import generate_latex

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "simple"


def make_proof() -> Proof:
    """Build a small synthetic Proof for output tests."""
    games = [
        Game(label="G0", latex_name=r"$\REAL()$", description="Starting game."),
        Game(label="G1", latex_name="Game~1", description="Modified game."),
        Game(label="G2", latex_name="Game~2", description="Final game."),
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
