"""Tests for texfrog.deps — external dependency checking."""

from __future__ import annotations

from unittest import mock

import pytest

from texfrog.deps import MissingDependencyError, check_html_deps


def _which_side_effect(available: set[str]):
    """Return a shutil.which mock that only finds tools in *available*."""
    def _which(name):
        return f"/usr/bin/{name}" if name in available else None
    return _which


class TestCheckHtmlDeps:
    """Tests for check_html_deps()."""

    @mock.patch("texfrog.deps.shutil.which")
    def test_all_present_pdftocairo(self, mock_which):
        mock_which.side_effect = _which_side_effect(
            {"pdflatex", "pdftocairo", "pdfcrop"}
        )
        assert check_html_deps() == "pdftocairo"

    @mock.patch("texfrog.deps.shutil.which")
    def test_all_present_pdf2svg(self, mock_which):
        mock_which.side_effect = _which_side_effect(
            {"pdflatex", "pdf2svg", "pdfcrop"}
        )
        assert check_html_deps() == "pdf2svg"

    @mock.patch("texfrog.deps.shutil.which")
    def test_prefers_pdftocairo_over_pdf2svg(self, mock_which):
        mock_which.side_effect = _which_side_effect(
            {"pdflatex", "pdftocairo", "pdf2svg", "pdfcrop"}
        )
        assert check_html_deps() == "pdftocairo"

    @mock.patch("texfrog.deps.shutil.which")
    def test_missing_pdflatex(self, mock_which):
        mock_which.side_effect = _which_side_effect({"pdftocairo", "pdfcrop"})
        with pytest.raises(MissingDependencyError, match="pdflatex not found"):
            check_html_deps()

    @mock.patch("texfrog.deps.shutil.which")
    def test_missing_svg_converter(self, mock_which):
        mock_which.side_effect = _which_side_effect({"pdflatex", "pdfcrop"})
        with pytest.raises(MissingDependencyError, match="pdftocairo nor pdf2svg"):
            check_html_deps()

    @mock.patch("texfrog.deps.shutil.which")
    def test_missing_both(self, mock_which):
        mock_which.side_effect = _which_side_effect({"pdfcrop"})
        with pytest.raises(MissingDependencyError) as exc_info:
            check_html_deps()
        msg = str(exc_info.value)
        assert "pdflatex" in msg
        assert "pdftocairo" in msg

    @mock.patch("texfrog.deps.shutil.which")
    def test_missing_pdfcrop_warns(self, mock_which, capsys):
        mock_which.side_effect = _which_side_effect({"pdflatex", "pdftocairo"})
        result = check_html_deps()
        assert result == "pdftocairo"
        captured = capsys.readouterr()
        assert "pdfcrop not found" in captured.err

    @mock.patch("texfrog.deps.platform.system", return_value="Darwin")
    @mock.patch("texfrog.deps.shutil.which")
    def test_macos_hints(self, mock_which, _mock_sys):
        mock_which.side_effect = _which_side_effect(set())
        with pytest.raises(MissingDependencyError) as exc_info:
            check_html_deps()
        msg = str(exc_info.value)
        assert "brew install" in msg

    @mock.patch("texfrog.deps.platform.system", return_value="Linux")
    @mock.patch("texfrog.deps.shutil.which")
    def test_linux_hints(self, mock_which, _mock_sys):
        mock_which.side_effect = _which_side_effect(set())
        with pytest.raises(MissingDependencyError) as exc_info:
            check_html_deps()
        msg = str(exc_info.value)
        assert "apt install" in msg
