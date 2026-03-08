"""Tests for texfrog.tex_parser — parsing .tex files with TeXFrog commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.tex_parser import (
    find_brace_group,
    find_bracket_group,
    resolve_tag_ranges,
    resolve_tfonly,
    filter_for_game_from_text,
    parse_tex_proof,
    parse_tex_proofs,
    _extract_one_arg,
    _extract_two_args,
    _extract_three_args,
    _extract_opt_two_args,
    _extract_one_plus_opt_two_args,
    _extract_tfsource,
    _extract_texfrog_package_option,
)


# ---------------------------------------------------------------------------
# resolve_tag_ranges
# ---------------------------------------------------------------------------

TAG_LABELS = ["G0", "G1", "Red1", "G2", "G3", "G4", "G5"]


def test_single_label():
    assert resolve_tag_ranges("G1", TAG_LABELS) == frozenset({"G1"})


def test_multiple_labels():
    assert resolve_tag_ranges("G0,G2", TAG_LABELS) == frozenset({"G0", "G2"})


def test_simple_range():
    assert resolve_tag_ranges("G1-G3", TAG_LABELS) == frozenset({"G1", "Red1", "G2", "G3"})


def test_range_spanning_reduction():
    assert resolve_tag_ranges("G0-Red1", TAG_LABELS) == frozenset({"G0", "G1", "Red1"})


def test_range_start_equals_end():
    assert resolve_tag_ranges("G2-G2", TAG_LABELS) == frozenset({"G2"})


def test_range_full_list():
    assert resolve_tag_ranges("G0-G5", TAG_LABELS) == frozenset(TAG_LABELS)


def test_mixed_single_and_range():
    assert resolve_tag_ranges("G0,G3-G5", TAG_LABELS) == frozenset({"G0", "G3", "G4", "G5"})


def test_reversed_range_raises():
    with pytest.raises(ValueError, match="reversed"):
        resolve_tag_ranges("G3-G1", TAG_LABELS)


def test_whitespace_around_tokens():
    assert resolve_tag_ranges(" G0 , G2 ", TAG_LABELS) == frozenset({"G0", "G2"})


def test_unknown_label_accepted_verbatim():
    # Unknown labels are passed through without error (user responsibility)
    result = resolve_tag_ranges("G0,UNKNOWN", TAG_LABELS)
    assert "G0" in result
    assert "UNKNOWN" in result


# ---------------------------------------------------------------------------
# Brace/bracket helpers
# ---------------------------------------------------------------------------


class TestFindBraceGroup:
    def test_simple(self):
        content, end = find_brace_group("{hello}", 0)
        assert content == "hello"
        assert end == 7

    def test_nested(self):
        content, end = find_brace_group("{a{b}c}", 0)
        assert content == "a{b}c"
        assert end == 7

    def test_with_backslash(self):
        content, end = find_brace_group(r"{a\}b}", 0)
        assert content == r"a\}b"
        assert end == 6

    def test_offset(self):
        content, end = find_brace_group("xx{hi}yy", 2)
        assert content == "hi"
        assert end == 6

    def test_not_brace(self):
        with pytest.raises(ValueError, match="Expected '{'"):
            find_brace_group("hello", 0)

    def test_unbalanced(self):
        with pytest.raises(ValueError, match="Unbalanced"):
            find_brace_group("{hello", 0)


class TestFindBracketGroup:
    def test_simple(self):
        content, end = find_bracket_group("[opt]", 0)
        assert content == "opt"
        assert end == 5

    def test_nested(self):
        content, end = find_bracket_group("[a[b]c]", 0)
        assert content == "a[b]c"
        assert end == 7


# ---------------------------------------------------------------------------
# Command extraction
# ---------------------------------------------------------------------------


class TestExtractOneArg:
    def test_simple(self):
        text = r"\tfmacrofile{macros.tex}"
        result = _extract_one_arg(text, "tfmacrofile")
        assert result == ["macros.tex"]

    def test_multiple(self):
        text = r"\tfmacrofile{a.tex} \tfmacrofile{b.tex}"
        result = _extract_one_arg(text, "tfmacrofile")
        assert result == ["a.tex", "b.tex"]

    def test_no_match(self):
        result = _extract_one_arg("no commands here", "tfmacrofile")
        assert result == []

    def test_partial_name_not_matched(self):
        text = r"\tfmacrofilefoo{bar}"
        result = _extract_one_arg(text, "tfmacrofile")
        assert result == []


class TestExtractTexfrogPackageOption:
    def test_cryptocode(self):
        text = r"\usepackage[package=cryptocode]{texfrog}"
        assert _extract_texfrog_package_option(text) == "cryptocode"

    def test_nicodemus(self):
        text = r"\usepackage[package=nicodemus]{texfrog}"
        assert _extract_texfrog_package_option(text) == "nicodemus"

    def test_no_option(self):
        text = r"\usepackage{texfrog}"
        assert _extract_texfrog_package_option(text) is None

    def test_multiple_options(self):
        text = r"\usepackage[other=foo,package=nicodemus]{texfrog}"
        assert _extract_texfrog_package_option(text) == "nicodemus"

    def test_no_package_key(self):
        text = r"\usepackage[other=foo]{texfrog}"
        assert _extract_texfrog_package_option(text) is None


class TestExtractTwoArgs:
    def test_simple(self):
        text = r"\tfgames{s}{G0,G1}"
        result = _extract_two_args(text, "tfgames")
        assert result == [("s", "G0,G1")]

    def test_with_latex_content(self):
        text = r"\tfreduction{s}{Red1}"
        result = _extract_two_args(text, "tfreduction")
        assert result == [("s", "Red1")]


class TestExtractThreeArgs:
    def test_simple(self):
        text = r"\tfgamename{s}{G0}{G_0}"
        result = _extract_three_args(text, "tfgamename")
        assert result == [("s", "G0", "G_0")]

    def test_with_latex_content(self):
        text = r"\tfgamename{s}{Red1}{\mathcal{B}_1}"
        result = _extract_three_args(text, "tfgamename")
        assert result == [("s", "Red1", r"\mathcal{B}_1")]


class TestExtractOptTwoArgs:
    def test_no_opt(self):
        text = r"\tffigure{all}{G0,G1}"
        result = _extract_opt_two_args(text, "tffigure")
        assert result == [(None, "all", "G0,G1")]

    def test_with_opt(self):
        text = r"\tffigure[My Figure]{all}{G0,G1}"
        result = _extract_opt_two_args(text, "tffigure")
        assert result == [("My Figure", "all", "G0,G1")]


class TestExtractOnePlusOptTwoArgs:
    def test_no_opt(self):
        text = r"\tffigure{s}{all}{G0,G1}"
        result = _extract_one_plus_opt_two_args(text, "tffigure")
        assert result == [("s", None, "all", "G0,G1")]

    def test_with_opt(self):
        text = r"\tffigure{s}[My Figure]{all}{G0,G1}"
        result = _extract_one_plus_opt_two_args(text, "tffigure")
        assert result == [("s", "My Figure", "all", "G0,G1")]


# ---------------------------------------------------------------------------
# tfsource extraction
# ---------------------------------------------------------------------------


class TestExtractTfsource:
    def test_simple(self):
        text = r"\begin{tfsource}{myproof}BODY\end{tfsource}"
        result = _extract_tfsource(text)
        assert result == {"myproof": "BODY"}

    def test_multiline(self):
        text = "\\begin{tfsource}{src}\nline1\nline2\n\\end{tfsource}"
        result = _extract_tfsource(text)
        assert "line1\nline2\n" in result["src"]

    def test_unterminated(self):
        text = r"\begin{tfsource}{src}BODY"
        with pytest.raises(ValueError, match="Unterminated"):
            _extract_tfsource(text)


# ---------------------------------------------------------------------------
# resolve_tfonly
# ---------------------------------------------------------------------------


LABELS = ["G0", "G1", "Red1", "G2"]


class TestResolveTfonly:
    def test_matching_game(self):
        src = r"\tfonly{G0}{content for G0}"
        result = resolve_tfonly(src, "G0", LABELS)
        assert result == "content for G0"

    def test_non_matching_game(self):
        src = r"\tfonly{G0}{content for G0}"
        result = resolve_tfonly(src, "G1", LABELS)
        assert result == ""

    def test_bare_text_preserved(self):
        src = "bare text"
        result = resolve_tfonly(src, "G0", LABELS)
        assert result == "bare text"

    def test_mixed(self):
        src = r"before \tfonly{G0}{AAA} middle \tfonly{G1}{BBB} after"
        result = resolve_tfonly(src, "G0", LABELS)
        assert result == "before AAA middle  after"

    def test_range(self):
        src = r"\tfonly{G0-G1}{shared}"
        result_g0 = resolve_tfonly(src, "G0", LABELS)
        result_g1 = resolve_tfonly(src, "G1", LABELS)
        result_g2 = resolve_tfonly(src, "G2", LABELS)
        assert result_g0 == "shared"
        assert result_g1 == "shared"
        assert result_g2 == ""

    def test_comma_list(self):
        src = r"\tfonly{G0,G2}{listed}"
        assert resolve_tfonly(src, "G0", LABELS) == "listed"
        assert resolve_tfonly(src, "G2", LABELS) == "listed"
        assert resolve_tfonly(src, "G1", LABELS) == ""

    def test_nested_braces(self):
        src = r"\tfonly{G0}{y \gets f\{k\}}"
        result = resolve_tfonly(src, "G0", LABELS)
        assert result == r"y \gets f\{k\}"

    def test_multiple_consecutive(self):
        src = (
            r"\tfonly{G0}{Game $G_0$}%"
            "\n"
            r"\tfonly{G1}{Game $G_1$}%"
        )
        result = resolve_tfonly(src, "G0", LABELS)
        assert "Game $G_0$" in result
        assert "Game $G_1$" not in result

    def test_missing_brace_raises(self):
        src = r"\tfonly G0 content"
        with pytest.raises(ValueError, match="Expected '{'"):
            resolve_tfonly(src, "G0", LABELS)

    def test_star_variant_behaves_like_tfonly(self):
        src = r"\tfonly*{G0}{content for G0}"
        assert resolve_tfonly(src, "G0", LABELS) == "content for G0"
        assert resolve_tfonly(src, "G1", LABELS) == ""

    def test_star_variant_mixed(self):
        src = r"\tfonly*{G0}{AAA}\tfonly{G1}{BBB}"
        assert resolve_tfonly(src, "G0", LABELS) == "AAA"
        assert resolve_tfonly(src, "G1", LABELS) == "BBB"

    def test_tffigonly_stripped(self):
        src = r"\tffigonly{Figure title}"
        assert resolve_tfonly(src, "G0", LABELS) == ""

    def test_tffigonly_with_surrounding_text(self):
        src = r"before \tffigonly{hidden} after"
        assert resolve_tfonly(src, "G0", LABELS) == "before  after"

    def test_star_and_tffigonly_combined(self):
        src = (
            r"\tfonly*{G0}{Game $G_0$}%"
            "\n"
            r"\tfonly*{G1}{Game $G_1$}%"
            "\n"
            r"\tffigonly{Games $G_0$--$G_1$}%"
        )
        result = resolve_tfonly(src, "G0", LABELS)
        assert "Game $G_0$" in result
        assert "Game $G_1$" not in result
        assert "Games $G_0$--$G_1$" not in result

    def test_tffigonly_nested_braces(self):
        src = r"\tffigonly{Games $\mathcal{A}$}"
        assert resolve_tfonly(src, "G0", LABELS) == ""


# ---------------------------------------------------------------------------
# filter_for_game_from_text
# ---------------------------------------------------------------------------


class TestFilterForGameFromText:
    def test_basic(self):
        src = (
            "\\begin{pcvstack}\n"
            "  \\tfonly{G0}{line1 \\\\}\n"
            "  common \\\\\n"
            "  \\pcreturn x\n"
            "\\end{pcvstack}"
        )
        lines = filter_for_game_from_text(src, "G0", LABELS)
        # Should contain the resolved content
        joined = "\n".join(lines)
        assert "line1" in joined
        assert "common" in joined

    def test_strips_trailing_separator(self):
        src = "  a \\\\\n  b \\\\"
        lines = filter_for_game_from_text(src, "G0", LABELS)
        # Last non-empty line should NOT end with \\
        non_empty = [l for l in lines if l.strip()]
        if non_empty:
            assert not non_empty[-1].rstrip().endswith("\\\\")


# ---------------------------------------------------------------------------
# parse_tex_proof (integration)
# ---------------------------------------------------------------------------


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestParseTexProof:
    def test_tutorial_cryptocode_quickstart(self):
        tex_path = _PROJECT_ROOT / "examples" / "tutorial-cryptocode-quickstart" / "main.tex"
        proof = parse_tex_proof(tex_path)
        assert proof.package == "cryptocode"
        assert len(proof.games) == 5
        assert proof.games[0].label == "G0"
        assert proof.games[0].latex_name == "G_0"
        assert proof.games[2].label == "Red1"
        assert proof.games[2].reduction is True
        assert proof.games[2].related_games == ["G0", "G1"]
        assert proof.source_text is not None
        assert len(proof.source_text) > 0
        assert proof.macros == ["macros.tex"]

    def test_missing_tfgames_raises(self, tmp_path):
        tex = tmp_path / "bad.tex"
        tex.write_text(
            r"\begin{tfsource}{s}body\end{tfsource}",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match=r"Source 's' has no \\tfgames definition"):
            parse_tex_proof(tex)

    def test_missing_tfsource_raises(self, tmp_path):
        tex = tmp_path / "bad.tex"
        tex.write_text(r"\tfgames{s}{G0}", encoding="utf-8")
        with pytest.raises(ValueError, match="tfsource"):
            parse_tex_proof(tex)

    def test_unsafe_label_raises(self, tmp_path):
        tex = tmp_path / "bad.tex"
        tex.write_text(
            "\\tfgames{s}{G 0}\n"
            "\\begin{tfsource}{s}body\\end{tfsource}",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="unsafe characters"):
            parse_tex_proof(tex)

    def test_related_games_on_non_reduction_raises(self, tmp_path):
        tex = tmp_path / "bad.tex"
        tex.write_text(
            "\\tfgames{s}{G0, G1}\n"
            "\\tfrelatedgames{s}{G0}{G1}\n"
            "\\begin{tfsource}{s}body\\end{tfsource}",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="not a reduction"):
            parse_tex_proof(tex)

    def test_unknown_related_game_raises(self, tmp_path):
        tex = tmp_path / "bad.tex"
        tex.write_text(
            "\\tfgames{s}{G0, Red1}\n"
            "\\tfreduction{s}{Red1}\n"
            "\\tfrelatedgames{s}{Red1}{G0, G99}\n"
            "\\begin{tfsource}{s}body\\end{tfsource}",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="unknown related game"):
            parse_tex_proof(tex)

    def test_multiple_tfsource_raises(self, tmp_path):
        tex = tmp_path / "multi.tex"
        tex.write_text(
            "\\tfgames{s1}{G0}\n"
            "\\tfgames{s2}{G1}\n"
            "\\begin{tfsource}{s1}body1\\end{tfsource}\n"
            "\\begin{tfsource}{s2}body2\\end{tfsource}",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Expected exactly one proof"):
            parse_tex_proof(tex)


# ---------------------------------------------------------------------------
# parse_tex_proofs — multi-proof documents
# ---------------------------------------------------------------------------


class TestParseTexProofsMulti:
    """Tests for documents with multiple independent proofs."""

    def _write_multiproof(self, tmp_path: Path) -> Path:
        """Write a minimal two-proof .tex document."""
        tex = tmp_path / "multi.tex"
        tex.write_text(
            "\\tfgames{alpha}{A0, A1}\n"
            "\\tfgamename{alpha}{A0}{A_0}\n"
            "\\tfgamename{alpha}{A1}{A_1}\n"
            "\\tfdescription{alpha}{A0}{First game of alpha.}\n"
            "\\tfdescription{alpha}{A1}{Second game of alpha.}\n"
            "\\tfmacrofile{macros.tex}\n"
            "\n"
            "\\tfgames{beta}{B0, B1, RedB}\n"
            "\\tfgamename{beta}{B0}{B_0}\n"
            "\\tfgamename{beta}{B1}{B_1}\n"
            "\\tfgamename{beta}{RedB}{\\mathcal{R}}\n"
            "\\tfdescription{beta}{B0}{First game of beta.}\n"
            "\\tfdescription{beta}{B1}{Second game of beta.}\n"
            "\\tfdescription{beta}{RedB}{Reduction in beta.}\n"
            "\\tfreduction{beta}{RedB}\n"
            "\\tfrelatedgames{beta}{RedB}{B0, B1}\n"
            "\n"
            "\\begin{tfsource}{alpha}\n"
            "  \\tfonly{A0}{alpha-line-A0}\n"
            "  \\tfonly{A1}{alpha-line-A1}\n"
            "  common-alpha\n"
            "\\end{tfsource}\n"
            "\n"
            "\\begin{tfsource}{beta}\n"
            "  \\tfonly{B0}{beta-line-B0}\n"
            "  \\tfonly{B1}{beta-line-B1}\n"
            "  common-beta\n"
            "\\end{tfsource}\n",
            encoding="utf-8",
        )
        return tex

    def test_returns_two_proofs(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        proofs = parse_tex_proofs(tex)
        assert len(proofs) == 2

    def test_proof_source_names(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        proofs = parse_tex_proofs(tex)
        names = {p.source_name for p in proofs}
        assert names == {"alpha", "beta"}

    def test_games_are_independent(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        proofs = parse_tex_proofs(tex)
        by_name = {p.source_name: p for p in proofs}
        alpha = by_name["alpha"]
        beta = by_name["beta"]
        assert [g.label for g in alpha.games] == ["A0", "A1"]
        assert [g.label for g in beta.games] == ["B0", "B1", "RedB"]

    def test_reductions_are_per_proof(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        proofs = parse_tex_proofs(tex)
        by_name = {p.source_name: p for p in proofs}
        # alpha has no reductions
        assert all(not g.reduction for g in by_name["alpha"].games)
        # beta has RedB as a reduction
        red = [g for g in by_name["beta"].games if g.reduction]
        assert len(red) == 1
        assert red[0].label == "RedB"
        assert red[0].related_games == ["B0", "B1"]

    def test_source_text_is_independent(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        proofs = parse_tex_proofs(tex)
        by_name = {p.source_name: p for p in proofs}
        assert "common-alpha" in by_name["alpha"].source_text
        assert "common-beta" not in by_name["alpha"].source_text
        assert "common-beta" in by_name["beta"].source_text
        assert "common-alpha" not in by_name["beta"].source_text

    def test_macros_shared_across_proofs(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        proofs = parse_tex_proofs(tex)
        for proof in proofs:
            assert "macros.tex" in proof.macros

    def test_descriptions_are_per_proof(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        proofs = parse_tex_proofs(tex)
        by_name = {p.source_name: p for p in proofs}
        alpha_g0 = by_name["alpha"].games[0]
        assert alpha_g0.description == "First game of alpha."
        beta_g0 = by_name["beta"].games[0]
        assert beta_g0.description == "First game of beta."

    def test_latex_names_are_per_proof(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        proofs = parse_tex_proofs(tex)
        by_name = {p.source_name: p for p in proofs}
        assert by_name["alpha"].games[0].latex_name == "A_0"
        assert by_name["beta"].games[0].latex_name == "B_0"

    def test_parse_tex_proof_rejects_multi(self, tmp_path):
        tex = self._write_multiproof(tmp_path)
        with pytest.raises(ValueError, match="Expected exactly one proof"):
            parse_tex_proof(tex)

    def test_example_multiproof(self):
        """The example-multiproof example should parse into two proofs."""
        example = Path(__file__).resolve().parent.parent / "examples" / "example-multiproof" / "main.tex"
        if not example.exists():
            pytest.skip("examples/example-multiproof not found")
        proofs = parse_tex_proofs(example)
        assert len(proofs) == 2
        names = {p.source_name for p in proofs}
        assert names == {"indcpa", "intctxt"}

    def test_tfsource_without_matching_tfgames_raises(self, tmp_path):
        """A tfsource block with no corresponding \\tfgames should error."""
        tex = tmp_path / "bad.tex"
        tex.write_text(
            "\\tfgames{alpha}{A0}\n"
            "\\begin{tfsource}{alpha}body\\end{tfsource}\n"
            "\\begin{tfsource}{orphan}body2\\end{tfsource}\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="orphan"):
            parse_tex_proofs(tex)

    def test_figures_are_per_proof(self, tmp_path):
        tex = tmp_path / "figs.tex"
        tex.write_text(
            "\\tfgames{p1}{X0, X1}\n"
            "\\tfgames{p2}{Y0, Y1}\n"
            "\\tffigure{p1}{fig1}{X0,X1}\n"
            "\\tffigure{p2}[My Title]{fig2}{Y0,Y1}\n"
            "\\begin{tfsource}{p1}body1\\end{tfsource}\n"
            "\\begin{tfsource}{p2}body2\\end{tfsource}\n",
            encoding="utf-8",
        )
        proofs = parse_tex_proofs(tex)
        by_name = {p.source_name: p for p in proofs}
        assert len(by_name["p1"].figures) == 1
        assert by_name["p1"].figures[0].label == "fig1"
        assert by_name["p1"].figures[0].procedure_name is None
        assert len(by_name["p2"].figures) == 1
        assert by_name["p2"].figures[0].label == "fig2"
        assert by_name["p2"].figures[0].procedure_name == "My Title"
