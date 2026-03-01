"""Tests for texfrog.parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.parser import parse_proof, parse_source_line, resolve_tag_ranges

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "simple"


# ---------------------------------------------------------------------------
# resolve_tag_ranges
# ---------------------------------------------------------------------------

LABELS = ["G0", "G1", "Red1", "G2", "G3", "G4", "G5"]


def test_single_label():
    assert resolve_tag_ranges("G1", LABELS) == frozenset({"G1"})


def test_multiple_labels():
    assert resolve_tag_ranges("G0,G2", LABELS) == frozenset({"G0", "G2"})


def test_simple_range():
    assert resolve_tag_ranges("G1-G3", LABELS) == frozenset({"G1", "Red1", "G2", "G3"})


def test_range_spanning_reduction():
    assert resolve_tag_ranges("G0-Red1", LABELS) == frozenset({"G0", "G1", "Red1"})


def test_range_start_equals_end():
    assert resolve_tag_ranges("G2-G2", LABELS) == frozenset({"G2"})


def test_range_full_list():
    assert resolve_tag_ranges("G0-G5", LABELS) == frozenset(LABELS)


def test_mixed_single_and_range():
    assert resolve_tag_ranges("G0,G3-G5", LABELS) == frozenset({"G0", "G3", "G4", "G5"})


def test_reversed_range_raises():
    with pytest.raises(ValueError, match="reversed"):
        resolve_tag_ranges("G3-G1", LABELS)


def test_whitespace_around_tokens():
    assert resolve_tag_ranges(" G0 , G2 ", LABELS) == frozenset({"G0", "G2"})


def test_unknown_label_accepted_verbatim():
    # Unknown labels are passed through without error (user responsibility)
    result = resolve_tag_ranges("G0,UNKNOWN", LABELS)
    assert "G0" in result
    assert "UNKNOWN" in result


# ---------------------------------------------------------------------------
# parse_source_line
# ---------------------------------------------------------------------------

def test_no_tag_gives_none():
    line = r"    (\pk, \sk) \getsr \KEM.\keygen() \\"
    sl = parse_source_line(line, LABELS)
    assert sl.tags is None
    assert sl.content == line


def test_tag_stripped_from_content():
    line = r"    (\ct^*, \key) \getsr \KEM.\encaps(\pk) \\ %:tags: G0,G1"
    sl = parse_source_line(line, LABELS)
    assert sl.tags == frozenset({"G0", "G1"})
    assert "%:tags:" not in sl.content
    assert sl.content == r"    (\ct^*, \key) \getsr \KEM.\encaps(\pk) \\"


def test_tag_range_in_source_line():
    line = r"    \key \gets F(\key_A) \\ %:tags: G0-G2"
    sl = parse_source_line(line, LABELS)
    assert sl.tags == frozenset({"G0", "G1", "Red1", "G2"})


def test_original_preserved():
    line = r"    some line %:tags: G1"
    sl = parse_source_line(line, LABELS)
    assert sl.original == line


# ---------------------------------------------------------------------------
# parse_proof (integration)
# ---------------------------------------------------------------------------

def test_parse_proof_games():
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    labels = [g.label for g in proof.games]
    assert labels == ["G0", "G1", "Red1", "G2"]


def test_parse_proof_macros():
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    assert proof.macros == ["macros.tex"]


def test_parse_proof_source_lines_loaded():
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    assert len(proof.source_lines) > 0


def test_parse_proof_commentary():
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    assert "G0" in proof.commentary
    assert "starting game" in proof.commentary["G0"]
    assert "G1" in proof.commentary


def test_parse_proof_figures():
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    assert len(proof.figures) == 2
    fig = next(f for f in proof.figures if f.label == "start_end")
    assert fig.games == ["G0", "G2"]


def test_parse_proof_figure_preserves_order():
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    fig = next(f for f in proof.figures if f.label == "with_reduction")
    # "G1,G2,Red1" should be reordered to game list order: G1, Red1, G2
    assert fig.games == ["G1", "Red1", "G2"]


def test_parse_proof_missing_source_raises(tmp_path):
    import shutil
    dest = tmp_path / "proof.yaml"
    shutil.copy(FIXTURE_DIR / "proof.yaml", dest)
    # Don't copy source.tex — should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        parse_proof(dest)
