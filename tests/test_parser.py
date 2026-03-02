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


# ---------------------------------------------------------------------------
# related_games
# ---------------------------------------------------------------------------

def test_parse_proof_related_games():
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    red1 = next(g for g in proof.games if g.label == "Red1")
    assert red1.related_games == ["G1", "G2"]


def test_parse_proof_related_games_default_empty():
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    g0 = next(g for g in proof.games if g.label == "G0")
    assert g0.related_games == []


def test_related_games_on_non_reduction_raises(tmp_path):
    """related_games is only valid on entries with reduction: true."""
    import yaml
    data = {
        "macros": [],
        "source": "source.tex",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test",
             "related_games": ["G1"]},
            {"label": "G1", "latex_name": "G_1", "description": "test"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="not a reduction"):
        parse_proof(yaml_path)


def test_related_games_too_many_raises(tmp_path):
    """related_games must have at most 2 entries."""
    import yaml
    data = {
        "macros": [],
        "source": "source.tex",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test"},
            {"label": "G1", "latex_name": "G_1", "description": "test"},
            {"label": "G2", "latex_name": "G_2", "description": "test"},
            {"label": "Red1", "latex_name": "R_1", "description": "test",
             "reduction": True, "related_games": ["G0", "G1", "G2"]},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="maximum is 2"):
        parse_proof(yaml_path)


def test_related_games_unknown_label_raises(tmp_path):
    """related_games labels must exist in the games list."""
    import yaml
    data = {
        "macros": [],
        "source": "source.tex",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test"},
            {"label": "Red1", "latex_name": "R_1", "description": "test",
             "reduction": True, "related_games": ["G99"]},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="unknown related game"):
        parse_proof(yaml_path)


# ---------------------------------------------------------------------------
# Package and preamble fields
# ---------------------------------------------------------------------------

NICO_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "nicodemus"


def test_parse_proof_default_package():
    """Default package should be 'cryptocode'."""
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    assert proof.package == "cryptocode"


def test_parse_proof_nicodemus_package():
    """Nicodemus fixture should have package='nicodemus'."""
    proof = parse_proof(NICO_FIXTURE_DIR / "proof.yaml")
    assert proof.package == "nicodemus"


def test_parse_proof_unknown_package_raises(tmp_path):
    """Unknown package name should raise ValueError."""
    import yaml
    data = {
        "package": "nonexistent",
        "macros": [],
        "source": "source.tex",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="Unknown package"):
        parse_proof(yaml_path)


def test_parse_proof_preamble_default_none():
    """No preamble field means proof.preamble is None."""
    proof = parse_proof(FIXTURE_DIR / "proof.yaml")
    assert proof.preamble is None


def test_parse_proof_nicodemus_source_lines():
    """Nicodemus fixture should parse source lines correctly."""
    proof = parse_proof(NICO_FIXTURE_DIR / "proof.yaml")
    assert len(proof.source_lines) > 0
    # Should have a line tagged for Red1
    red1_lines = [sl for sl in proof.source_lines if sl.tags and "Red1" in sl.tags]
    assert len(red1_lines) > 0


# ---------------------------------------------------------------------------
# Security: label validation
# ---------------------------------------------------------------------------

def test_game_label_with_path_traversal_raises(tmp_path):
    """Game labels containing path traversal characters must be rejected."""
    import yaml
    data = {
        "macros": [],
        "source": "source.tex",
        "games": [
            {"label": "../../evil", "latex_name": "E", "description": "test"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="unsafe characters"):
        parse_proof(yaml_path)


def test_game_label_with_slash_raises(tmp_path):
    """Game labels containing slashes must be rejected."""
    import yaml
    data = {
        "macros": [],
        "source": "source.tex",
        "games": [
            {"label": "G0/bad", "latex_name": "G_0", "description": "test"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="unsafe characters"):
        parse_proof(yaml_path)


def test_figure_label_with_path_traversal_raises(tmp_path):
    """Figure labels containing path traversal characters must be rejected."""
    import yaml
    data = {
        "macros": [],
        "source": "source.tex",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test"},
        ],
        "figures": [
            {"label": "../../evil", "games": "G0"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="unsafe characters"):
        parse_proof(yaml_path)


def test_valid_labels_accepted(tmp_path):
    """Labels with alphanumeric, underscore, and hyphen characters should work."""
    import yaml
    data = {
        "macros": [],
        "source": "source.tex",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test"},
            {"label": "Red-1", "latex_name": "R_1", "description": "test",
             "reduction": True},
            {"label": "Game_2", "latex_name": "G_2", "description": "test"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    proof = parse_proof(yaml_path)
    assert len(proof.games) == 3


# ---------------------------------------------------------------------------
# Security: path traversal checks
# ---------------------------------------------------------------------------

def test_macro_path_traversal_raises(tmp_path):
    """Macro paths that escape the proof directory must be rejected."""
    import yaml
    data = {
        "macros": ["../../etc/passwd"],
        "source": "source.tex",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="outside the proof directory"):
        parse_proof(yaml_path)


def test_preamble_path_traversal_raises(tmp_path):
    """Preamble paths that escape the proof directory must be rejected."""
    import yaml
    data = {
        "macros": [],
        "preamble": "../../etc/passwd",
        "source": "source.tex",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    (tmp_path / "source.tex").write_text("")
    with pytest.raises(ValueError, match="outside the proof directory"):
        parse_proof(yaml_path)


def test_source_path_traversal_raises(tmp_path):
    """Source paths that escape the proof directory must be rejected."""
    import yaml
    data = {
        "macros": [],
        "source": "../../etc/passwd",
        "games": [
            {"label": "G0", "latex_name": "G_0", "description": "test"},
        ],
    }
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml.dump(data))
    with pytest.raises(ValueError, match="outside the proof directory"):
        parse_proof(yaml_path)
