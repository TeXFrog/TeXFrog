"""CLI tests for the ``texfrog check`` command."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from texfrog.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_minimal_proof(tmp_path: Path, *, extra_yaml: str = "") -> Path:
    """Write a minimal valid proof and return the YAML path."""
    source = tmp_path / "source.tex"
    source.write_text(
        "common line\n"
        "only G0 %:tags: G0\n"
        "only G1 %:tags: G1\n",
        encoding="utf-8",
    )
    yaml_content = (
        "source: source.tex\n"
        "games:\n"
        "  - label: G0\n"
        "    latex_name: G_0\n"
        "    description: Game 0\n"
        "  - label: G1\n"
        "    latex_name: G_1\n"
        "    description: Game 1\n"
    )
    if extra_yaml:
        yaml_content += extra_yaml
    yaml_path = tmp_path / "proof.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")
    return yaml_path


class TestCheckCommand:
    """Tests for ``texfrog check``."""

    def test_valid_proof(self, tmp_path):
        yaml_path = _write_minimal_proof(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(yaml_path)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_invalid_yaml_missing_games(self, tmp_path):
        yaml_path = tmp_path / "proof.yaml"
        source = tmp_path / "source.tex"
        source.write_text("line\n", encoding="utf-8")
        yaml_path.write_text("source: source.tex\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(yaml_path)])
        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_warnings_exit_0_by_default(self, tmp_path):
        """Proof with warnings should exit 0 without --strict."""
        commentary_dir = tmp_path / "commentary"
        commentary_dir.mkdir()
        (commentary_dir / "G99.tex").write_text("orphan\n", encoding="utf-8")
        yaml_path = _write_minimal_proof(
            tmp_path,
            extra_yaml="commentary:\n  G99: commentary/G99.tex\n",
        )
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(yaml_path)])
        assert result.exit_code == 0
        assert "warning" in result.output.lower()

    def test_warnings_exit_1_with_strict(self, tmp_path):
        """Proof with warnings should exit 1 with --strict."""
        commentary_dir = tmp_path / "commentary"
        commentary_dir.mkdir()
        (commentary_dir / "G99.tex").write_text("orphan\n", encoding="utf-8")
        yaml_path = _write_minimal_proof(
            tmp_path,
            extra_yaml="commentary:\n  G99: commentary/G99.tex\n",
        )
        runner = CliRunner()
        result = runner.invoke(main, ["check", "--strict", str(yaml_path)])
        assert result.exit_code == 1

    def test_directory_input(self, tmp_path):
        """Passing a directory should resolve to proof.yaml inside it."""
        _write_minimal_proof(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tmp_path)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_tutorial_cryptocode_strict(self):
        """The cryptocode tutorial should pass in strict mode."""
        tutorial = REPO_ROOT / "examples" / "tutorial-cryptocode" / "proof.yaml"
        if not tutorial.exists():
            pytest.skip("examples/tutorial-cryptocode not found")
        runner = CliRunner()
        result = runner.invoke(main, ["check", "--strict", str(tutorial)])
        assert result.exit_code == 0, result.output

    def test_tutorial_nicodemus_strict(self):
        """The nicodemus tutorial should pass in strict mode."""
        tutorial = REPO_ROOT / "examples" / "tutorial-nicodemus" / "proof.yaml"
        if not tutorial.exists():
            pytest.skip("examples/tutorial-nicodemus not found")
        runner = CliRunner()
        result = runner.invoke(main, ["check", "--strict", str(tutorial)])
        assert result.exit_code == 0, result.output
