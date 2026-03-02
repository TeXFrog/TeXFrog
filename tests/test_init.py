"""Tests for ``texfrog init``."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from texfrog.cli import main
from texfrog.parser import parse_proof
from texfrog.templates import get_templates


# ---------------------------------------------------------------------------
# Template content tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("package", ["cryptocode", "nicodemus"])
def test_get_templates_returns_expected_files(package: str):
    templates = get_templates(package)
    assert "proof.yaml" in templates
    assert "games_source.tex" in templates
    assert "macros.tex" in templates
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
    assert (target / "proof.yaml").exists()
    assert (target / "games_source.tex").exists()
    assert (target / "macros.tex").exists()
    assert "Created 3 file(s)" in result.output


def test_init_creates_files_in_existing_directory(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "proof.yaml").exists()


def test_init_nicodemus(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path), "--package", "nicodemus"])
    assert result.exit_code == 0
    yaml_content = (tmp_path / "proof.yaml").read_text()
    assert "package: nicodemus" in yaml_content
    source_content = (tmp_path / "games_source.tex").read_text()
    assert "nicodemusheader" in source_content


def test_init_cryptocode_is_default(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    yaml_content = (tmp_path / "proof.yaml").read_text()
    # Default cryptocode template has the line commented out
    assert "# package: cryptocode" in yaml_content
    source_content = (tmp_path / "games_source.tex").read_text()
    assert "pcvstack" in source_content


def test_init_skips_existing_files(tmp_path: Path):
    # Pre-create proof.yaml
    (tmp_path / "proof.yaml").write_text("existing content")
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "Skipping proof.yaml" in result.output
    # Should not overwrite existing file
    assert (tmp_path / "proof.yaml").read_text() == "existing content"
    # But should still create the other files
    assert (tmp_path / "games_source.tex").exists()
    assert (tmp_path / "macros.tex").exists()


def test_init_all_existing_writes_nothing(tmp_path: Path):
    for name in ("proof.yaml", "games_source.tex", "macros.tex"):
        (tmp_path / name).write_text("existing")
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "No files written" in result.output


def test_init_default_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "proof.yaml").exists()


# ---------------------------------------------------------------------------
# Round-trip: init → parse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("package", ["cryptocode", "nicodemus"])
def test_init_output_is_parseable(tmp_path: Path, package: str):
    """Scaffolded files can be parsed by the TeXFrog parser without errors."""
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path), "--package", package])
    assert result.exit_code == 0
    proof = parse_proof(tmp_path / "proof.yaml")
    assert len(proof.games) == 4
    assert proof.games[0].label == "G0"
    assert proof.games[1].label == "G1"
    assert proof.games[2].label == "Red1"
    assert proof.games[2].reduction is True
    assert proof.games[3].label == "G2"
    assert len(proof.source_lines) > 0
    assert len(proof.figures) == 1
