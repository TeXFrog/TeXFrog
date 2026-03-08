"""Tests for ``texfrog init``."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from texfrog.cli import main
from texfrog.tex_parser import parse_tex_proof
from texfrog.templates import get_templates


# ---------------------------------------------------------------------------
# Template content tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("package", ["cryptocode", "nicodemus"])
def test_get_templates_returns_expected_files(package: str):
    templates = get_templates(package)
    assert "proof.tex" in templates
    assert "macros.tex" in templates
    assert "commentary/G0.tex" in templates
    assert "commentary/G1.tex" in templates
    assert "commentary/Red1.tex" in templates
    assert "commentary/G2.tex" in templates
    for filename, (content, description) in templates.items():
        assert len(content) > 0
        assert len(description) > 0


def test_get_templates_unknown_package():
    with pytest.raises(ValueError, match="Unknown package"):
        get_templates("nonexistent")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_init_creates_files_in_new_directory(tmp_path: Path):
    target = tmp_path / "myproof"
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(target)])
    assert result.exit_code == 0
    assert (target / "proof.tex").exists()
    assert (target / "macros.tex").exists()
    assert (target / "commentary" / "G0.tex").exists()
    assert (target / "commentary" / "G1.tex").exists()
    assert (target / "commentary" / "Red1.tex").exists()
    assert (target / "commentary" / "G2.tex").exists()
    assert "Created 6 file(s)" in result.output


def test_init_creates_files_in_existing_directory(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "proof.tex").exists()


def test_init_nicodemus(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path), "--package", "nicodemus"])
    assert result.exit_code == 0
    tex_content = (tmp_path / "proof.tex").read_text()
    assert r"\tfsetpackage{nicodemus}" in tex_content
    assert "nicodemusheader" in tex_content


def test_init_cryptocode_is_default(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    tex_content = (tmp_path / "proof.tex").read_text()
    assert r"\tfsetpackage{cryptocode}" in tex_content
    assert "pcvstack" in tex_content


def test_init_skips_existing_files(tmp_path: Path):
    # Pre-create proof.tex
    (tmp_path / "proof.tex").write_text("existing content")
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "Skipping proof.tex" in result.output
    # Should not overwrite existing file
    assert (tmp_path / "proof.tex").read_text() == "existing content"
    # But should still create the other files
    assert (tmp_path / "macros.tex").exists()


def test_init_all_existing_writes_nothing(tmp_path: Path):
    for name in ("proof.tex", "macros.tex"):
        (tmp_path / name).write_text("existing")
    commentary_dir = tmp_path / "commentary"
    commentary_dir.mkdir()
    for name in ("G0.tex", "G1.tex", "Red1.tex", "G2.tex"):
        (commentary_dir / name).write_text("existing")
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "No files written" in result.output


def test_init_default_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "proof.tex").exists()


# ---------------------------------------------------------------------------
# Round-trip: init → parse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("package", ["cryptocode", "nicodemus"])
def test_init_output_is_parseable(tmp_path: Path, package: str):
    """Scaffolded files can be parsed by the TeXFrog parser without errors."""
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path), "--package", package])
    assert result.exit_code == 0
    proof = parse_tex_proof(tmp_path / "proof.tex")
    assert len(proof.games) == 4
    assert proof.games[0].label == "G0"
    assert proof.games[1].label == "G1"
    assert proof.games[2].label == "Red1"
    assert proof.games[2].reduction is True
    assert proof.games[3].label == "G2"
    assert proof.source_text is not None
    assert len(proof.source_text) > 0
