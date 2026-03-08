"""Tests for CLI helper functions in texfrog.cli."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from texfrog.cli import _resolve_input_path, _show_warnings, main
from texfrog.model import Game, Proof


# ---------------------------------------------------------------------------
# _resolve_input_path
# ---------------------------------------------------------------------------


class TestResolveInputPath:
    """Tests for _resolve_input_path."""

    def test_file_path_returned_as_is(self, tmp_path):
        tex_file = tmp_path / "proof.tex"
        tex_file.write_text("content", encoding="utf-8")
        result = _resolve_input_path(str(tex_file))
        assert result == tex_file.resolve()

    def test_directory_with_proof_tex(self, tmp_path):
        tex_file = tmp_path / "proof.tex"
        tex_file.write_text("content", encoding="utf-8")
        result = _resolve_input_path(str(tmp_path))
        assert result == tex_file.resolve()

    def test_directory_without_proof_tex_raises(self, tmp_path):
        with pytest.raises(click.BadParameter, match="does not contain a proof.tex"):
            _resolve_input_path(str(tmp_path))

    def test_resolves_to_absolute_path(self, tmp_path):
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("content", encoding="utf-8")
        result = _resolve_input_path(str(tex_file))
        assert result.is_absolute()

    def test_nonexistent_file_still_resolves(self, tmp_path):
        """Non-existent files are resolved (click handles existence checks)."""
        result = _resolve_input_path(str(tmp_path / "missing.tex"))
        assert result.is_absolute()


# ---------------------------------------------------------------------------
# _show_warnings
# ---------------------------------------------------------------------------


class TestShowWarnings:
    """Tests for _show_warnings."""

    def _make_proof(self, **kwargs) -> Proof:
        defaults = dict(
            source_name="main",
            macros=[],
            games=[
                Game(label="G0", latex_name="G_0", description="Game 0"),
                Game(label="G1", latex_name="G_1", description="Game 1"),
            ],
            source_text="common\n",
            commentary={},
            figures=[],
        )
        defaults.update(kwargs)
        return Proof(**defaults)

    def test_no_warnings_returns_empty(self, tmp_path):
        proof = self._make_proof()
        warnings = _show_warnings(proof, tmp_path)
        assert warnings == []

    def test_warnings_returned_as_list(self, tmp_path):
        # Commentary for a non-existent game triggers a warning
        proof = self._make_proof(
            commentary={"G99": "orphan commentary"},
            commentary_files={"G99": "commentary/G99.tex"},
        )
        warnings = _show_warnings(proof, tmp_path)
        assert len(warnings) > 0

    def test_warnings_echoed_to_stderr(self, tmp_path, capsys):
        proof = self._make_proof(
            commentary={"G99": "orphan commentary"},
            commentary_files={"G99": "commentary/G99.tex"},
        )
        _show_warnings(proof, tmp_path)
        captured = capsys.readouterr()
        assert "Warning:" in captured.err


# ---------------------------------------------------------------------------
# CLI html group
# ---------------------------------------------------------------------------


class TestHtmlGroup:
    """Tests for the html CLI group."""

    def test_html_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["html", "--help"])
        assert result.exit_code == 0
        assert "build" in result.output.lower()
        assert "serve" in result.output.lower()

    def test_html_build_missing_input(self):
        runner = CliRunner()
        result = runner.invoke(main, ["html", "build", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_html_serve_missing_input(self):
        runner = CliRunner()
        result = runner.invoke(main, ["html", "serve", "/nonexistent/path"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI edge cases
# ---------------------------------------------------------------------------


class TestCliEdgeCases:
    """Tests for CLI edge cases."""

    def test_main_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "texfrog" in result.output.lower()

    def test_check_nonexistent_file(self):
        runner = CliRunner()
        result = runner.invoke(main, ["check", "/nonexistent/file.tex"])
        assert result.exit_code != 0

    def test_check_directory_without_proof_tex(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tmp_path)])
        assert result.exit_code != 0
        assert "proof.tex" in result.output.lower() or "proof.tex" in (result.output + str(result.exception)).lower()
