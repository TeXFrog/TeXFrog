"""CLI tests for the ``texfrog check`` command."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from texfrog.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_minimal_proof(tmp_path: Path, *, extra_tex: str = "") -> Path:
    """Write a minimal valid .tex proof and return its path."""
    content = (
        r"\tfgames{G0, G1}" "\n"
        r"\tfgamename{G0}{G_0}" "\n"
        r"\tfgamename{G1}{G_1}" "\n"
        r"\tfdescription{G0}{Game 0}" "\n"
        r"\tfdescription{G1}{Game 1}" "\n"
        + extra_tex +
        r"\begin{tfsource}{main}" "\n"
        "common line\n"
        r"\tfonly{G0}{only G0}" "\n"
        r"\tfonly{G1}{only G1}" "\n"
        r"\end{tfsource}" "\n"
    )
    tex_path = tmp_path / "proof.tex"
    tex_path.write_text(content, encoding="utf-8")
    return tex_path


class TestCheckCommand:
    """Tests for ``texfrog check``."""

    def test_valid_proof(self, tmp_path):
        tex_path = _write_minimal_proof(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tex_path)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_invalid_missing_games(self, tmp_path):
        tex_path = tmp_path / "proof.tex"
        tex_path.write_text(
            r"\begin{tfsource}{main}" "\n"
            "line\n"
            r"\end{tfsource}" "\n",
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tex_path)])
        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_warnings_exit_0_by_default(self, tmp_path):
        """Proof with warnings should exit 0 without --strict."""
        commentary_dir = tmp_path / "commentary"
        commentary_dir.mkdir()
        (commentary_dir / "G99.tex").write_text("orphan\n", encoding="utf-8")
        tex_path = _write_minimal_proof(
            tmp_path,
            extra_tex=r"\tfcommentary{G99}{commentary/G99.tex}" "\n",
        )
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tex_path)])
        assert result.exit_code == 0
        assert "warning" in result.output.lower()

    def test_warnings_exit_1_with_strict(self, tmp_path):
        """Proof with warnings should exit 1 with --strict."""
        commentary_dir = tmp_path / "commentary"
        commentary_dir.mkdir()
        (commentary_dir / "G99.tex").write_text("orphan\n", encoding="utf-8")
        tex_path = _write_minimal_proof(
            tmp_path,
            extra_tex=r"\tfcommentary{G99}{commentary/G99.tex}" "\n",
        )
        runner = CliRunner()
        result = runner.invoke(main, ["check", "--strict", str(tex_path)])
        assert result.exit_code == 1

    def test_directory_input(self, tmp_path):
        """Passing a directory should resolve to proof.tex inside it."""
        _write_minimal_proof(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tmp_path)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_tutorial_cryptocode_strict(self):
        """The cryptocode tutorial should pass in strict mode."""
        tutorial = REPO_ROOT / "examples" / "tutorial-cryptocode" / "main.tex"
        if not tutorial.exists():
            pytest.skip("examples/tutorial-cryptocode not found")
        runner = CliRunner()
        result = runner.invoke(main, ["check", "--strict", str(tutorial)])
        assert result.exit_code == 0, result.output

    def test_tutorial_nicodemus_strict(self):
        """The nicodemus tutorial should pass in strict mode."""
        tutorial = REPO_ROOT / "examples" / "tutorial-nicodemus" / "main.tex"
        if not tutorial.exists():
            pytest.skip("examples/tutorial-nicodemus not found")
        runner = CliRunner()
        result = runner.invoke(main, ["check", "--strict", str(tutorial)])
        assert result.exit_code == 0, result.output
