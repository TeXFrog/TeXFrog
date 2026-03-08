"""Tests for internal functions in texfrog.output.html."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from texfrog.model import Game, Proof
from texfrog.output.html import (
    _build_wrapper_template,
    _extract_mathjax_macros,
    _find_svg_converter,
    _load_template_resource,
    _pdf_to_svg,
    _write_commentary_file,
    generate_index_page,
)


# ---------------------------------------------------------------------------
# _write_commentary_file
# ---------------------------------------------------------------------------


class TestWriteCommentaryFile:
    """Tests for _write_commentary_file."""

    def test_writes_file_with_header_comment(self, tmp_path):
        out = tmp_path / "G0_commentary.tex"
        _write_commentary_file("G0", "Some commentary text.\n", out)
        content = out.read_text(encoding="utf-8")
        assert content.startswith("% TeXFrog commentary for game: G0\n")
        assert "Some commentary text." in content

    def test_preserves_raw_text(self, tmp_path):
        raw = r"\begin{claim}Foo.\end{claim}" + "\n"
        out = tmp_path / "G1_commentary.tex"
        _write_commentary_file("G1", raw, out)
        content = out.read_text(encoding="utf-8")
        assert raw in content

    def test_label_in_comment(self, tmp_path):
        out = tmp_path / "Red1_commentary.tex"
        _write_commentary_file("Red1", "text", out)
        content = out.read_text(encoding="utf-8")
        assert "Red1" in content.splitlines()[0]


# ---------------------------------------------------------------------------
# _build_wrapper_template
# ---------------------------------------------------------------------------


class TestBuildWrapperTemplate:
    """Tests for _build_wrapper_template."""

    def test_cryptocode_includes_highlighting(self):
        tmpl = _build_wrapper_template("cryptocode")
        assert r"\newcommand{{\tfchanged}}" in tmpl or r"\tfchanged" in tmpl
        assert r"\highlightbox" in tmpl
        assert r"\tfremoved" in tmpl
        assert r"\tfgamelabel" in tmpl

    def test_nicodemus_includes_highlighting(self):
        tmpl = _build_wrapper_template("nicodemus")
        assert r"\tfchanged" in tmpl
        assert r"\tfremoved" in tmpl
        # Nicodemus has procedure_header_cmd, so it should be defined
        assert "nicodemusheader" in tmpl

    def test_commentary_mode_omits_highlighting(self):
        tmpl = _build_wrapper_template("cryptocode", commentary=True)
        assert r"\tfchanged" not in tmpl
        assert r"\tfremoved" not in tmpl
        assert r"\tfgamelabel" not in tmpl
        assert r"\raggedright" in tmpl

    def test_non_commentary_omits_raggedright(self):
        tmpl = _build_wrapper_template("cryptocode", commentary=False)
        assert r"\raggedright" not in tmpl

    def test_has_document_structure(self):
        tmpl = _build_wrapper_template("cryptocode")
        assert r"\documentclass{{article}}" in tmpl
        assert r"\begin{{document}}" in tmpl
        assert r"\end{{document}}" in tmpl

    def test_has_placeholders(self):
        tmpl = _build_wrapper_template("cryptocode")
        assert "{macro_inputs}" in tmpl
        assert "{gamename_defs}" in tmpl
        assert "{game_file}" in tmpl

    def test_placeholders_are_fillable(self):
        tmpl = _build_wrapper_template("cryptocode")
        filled = tmpl.format(
            macro_inputs=r"\input{macros.tex}",
            gamename_defs="",
            game_file="game.tex",
        )
        assert r"\input{macros.tex}" in filled
        assert r"\input{game.tex}" in filled

    def test_user_preamble_included(self):
        preamble = r"\newcommand{\myfoo}{bar}"
        tmpl = _build_wrapper_template("cryptocode", user_preamble_content=preamble)
        # Braces get doubled for .format() escaping
        assert "myfoo" in tmpl

    def test_cryptocode_preamble_line(self):
        tmpl = _build_wrapper_template("cryptocode")
        assert "cryptocode" in tmpl

    def test_nicodemus_preamble_line(self):
        tmpl = _build_wrapper_template("nicodemus")
        assert "nicodemus" in tmpl

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError):
            _build_wrapper_template("bogus")


# ---------------------------------------------------------------------------
# _find_svg_converter
# ---------------------------------------------------------------------------


class TestFindSvgConverter:
    """Tests for _find_svg_converter."""

    def test_finds_pdf2svg(self):
        def mock_which(tool):
            return "/usr/bin/pdf2svg" if tool == "pdf2svg" else None

        with patch("shutil.which", side_effect=mock_which):
            assert _find_svg_converter() == "pdf2svg"

    def test_finds_pdftocairo(self):
        def mock_which(tool):
            return "/usr/bin/pdftocairo" if tool == "pdftocairo" else None

        with patch("shutil.which", side_effect=mock_which):
            assert _find_svg_converter() == "pdftocairo"

    def test_prefers_pdf2svg(self):
        with patch("shutil.which", return_value="/usr/bin/tool"):
            assert _find_svg_converter() == "pdf2svg"

    def test_returns_none_when_neither(self):
        with patch("shutil.which", return_value=None):
            assert _find_svg_converter() is None


# ---------------------------------------------------------------------------
# _pdf_to_svg
# ---------------------------------------------------------------------------


class TestPdfToSvg:
    """Tests for _pdf_to_svg."""

    def test_pdf2svg_command(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        svg = tmp_path / "test.svg"
        pdf.write_text("fake")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _pdf_to_svg(pdf, svg, "pdf2svg")
            args = mock_run.call_args[0][0]
            assert args[0] == "pdf2svg"
            assert str(pdf) in args
            assert str(svg) in args

    def test_pdftocairo_command(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        svg = tmp_path / "test.svg"
        pdf.write_text("fake")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _pdf_to_svg(pdf, svg, "pdftocairo")
            args = mock_run.call_args[0][0]
            assert args[0] == "pdftocairo"
            assert "-svg" in args

    def test_raises_on_failure(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        svg = tmp_path / "test.svg"
        pdf.write_text("fake")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "conversion error"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="conversion error"):
                _pdf_to_svg(pdf, svg, "pdf2svg")


# ---------------------------------------------------------------------------
# _extract_mathjax_macros
# ---------------------------------------------------------------------------


class TestExtractMathjaxMacros:
    """Tests for _extract_mathjax_macros."""

    def test_extracts_newcommand(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            r"\newcommand{\foo}{bar}" "\n"
            "% just a comment\n"
            r"\newcommand{\baz}[1]{#1}" "\n",
            encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        assert r"\newcommand{\foo}{bar}" in result
        assert r"\newcommand{\baz}[1]{#1}" in result
        assert "comment" not in result

    def test_extracts_renewcommand(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            r"\renewcommand{\bar}{baz}" "\n",
            encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        assert r"\renewcommand{\bar}{baz}" in result

    def test_extracts_providecommand(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            r"\providecommand{\qux}{val}" "\n",
            encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        assert r"\providecommand{\qux}{val}" in result

    def test_extracts_declaremathoperator(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            r"\DeclareMathOperator{\Enc}{Enc}" "\n",
            encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        assert r"\DeclareMathOperator{\Enc}{Enc}" in result

    def test_extracts_def(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            r"\def\myval{123}" "\n",
            encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        assert r"\def\myval{123}" in result

    def test_skips_multiline_definitions(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            r"\newcommand{\multi}{" "\n"
            r"  some content" "\n"
            "}\n",
            encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        # The opening line has unbalanced braces, so it should be skipped
        assert result == ""

    def test_skips_non_macro_lines(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            "% This is a comment\n"
            r"\usepackage{amsmath}" "\n"
            "some random text\n",
            encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        assert result == ""

    def test_multiple_files(self, tmp_path):
        (tmp_path / "a.tex").write_text(
            r"\newcommand{\aaa}{1}" "\n", encoding="utf-8"
        )
        (tmp_path / "b.tex").write_text(
            r"\newcommand{\bbb}{2}" "\n", encoding="utf-8"
        )
        result = _extract_mathjax_macros(["a.tex", "b.tex"], tmp_path)
        assert r"\aaa" in result
        assert r"\bbb" in result

    def test_missing_file_skipped(self, tmp_path):
        result = _extract_mathjax_macros(["nonexistent.tex"], tmp_path)
        assert result == ""

    def test_empty_macros_list(self, tmp_path):
        result = _extract_mathjax_macros([], tmp_path)
        assert result == ""


# ---------------------------------------------------------------------------
# _load_template_resource
# ---------------------------------------------------------------------------


class TestLoadTemplateResource:
    """Tests for _load_template_resource."""

    def test_loads_style_css(self):
        css = _load_template_resource("style.css")
        assert len(css) > 0
        # Should contain CSS-like content
        assert "{" in css

    def test_loads_app_js(self):
        js = _load_template_resource("app.js")
        assert len(js) > 0
        assert "function" in js


# ---------------------------------------------------------------------------
# generate_index_page
# ---------------------------------------------------------------------------


class TestGenerateIndexPage:
    """Tests for generate_index_page."""

    def _make_proof(self, name: str, n_games: int, n_reductions: int) -> Proof:
        games = []
        for i in range(n_games):
            games.append(Game(
                label=f"G{i}", latex_name=f"G_{i}", description=f"Game {i}",
            ))
        for i in range(n_reductions):
            games.append(Game(
                label=f"R{i}", latex_name=f"R_{i}", description=f"Red {i}",
                reduction=True,
            ))
        return Proof(
            source_name=name,
            macros=[],
            games=games,
            source_text="",
            commentary={},
            figures=[],
        )

    def test_creates_index_html(self, tmp_path):
        proofs = [self._make_proof("alpha", 2, 1)]
        generate_index_page(proofs, tmp_path)
        assert (tmp_path / "index.html").exists()

    def test_contains_proof_links(self, tmp_path):
        proofs = [
            self._make_proof("alpha", 2, 1),
            self._make_proof("beta", 3, 0),
        ]
        generate_index_page(proofs, tmp_path)
        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "alpha/index.html" in html
        assert "beta/index.html" in html

    def test_contains_game_counts(self, tmp_path):
        proofs = [self._make_proof("alpha", 2, 1)]
        generate_index_page(proofs, tmp_path)
        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "2 games" in html
        assert "1 reduction" in html

    def test_singular_game_count(self, tmp_path):
        proofs = [self._make_proof("alpha", 1, 0)]
        generate_index_page(proofs, tmp_path)
        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "1 game" in html
        assert "1 games" not in html

    def test_creates_output_dir(self, tmp_path):
        out = tmp_path / "subdir" / "output"
        proofs = [self._make_proof("alpha", 1, 0)]
        generate_index_page(proofs, out)
        assert (out / "index.html").exists()

    def test_escapes_html_in_name(self, tmp_path):
        proofs = [self._make_proof("<script>", 1, 0)]
        generate_index_page(proofs, tmp_path)
        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_valid_html_structure(self, tmp_path):
        proofs = [self._make_proof("alpha", 2, 0)]
        generate_index_page(proofs, tmp_path)
        html = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "TeXFrog" in html
