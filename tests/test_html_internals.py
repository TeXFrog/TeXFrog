"""Tests for internal functions in texfrog.output.html."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from texfrog.model import Game, Proof
from texfrog.output.html import (
    _BUILTIN_MATHJAX_MACROS,
    _apply_crop,
    _build_wrapper_template,
    _extract_mathjax_macros,
    _find_svg_converter,
    _load_template_resource,
    _pdf_to_svg,
    _reduction_active_segments,
    _write_commentary_file,
    generate_html,
    generate_index_page,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_NICODEMUS_STY = _PROJECT_ROOT / "resources" / "nicodemus.sty"

needs_pdflatex = pytest.mark.skipif(
    shutil.which("pdflatex") is None,
    reason="pdflatex not found on PATH",
)

needs_html_tools = pytest.mark.skipif(
    shutil.which("pdflatex") is None or _find_svg_converter() is None,
    reason="pdflatex and/or SVG converter (pdf2svg/pdftocairo) not on PATH",
)


# ---------------------------------------------------------------------------
# _write_commentary_file
# ---------------------------------------------------------------------------


def test_apply_crop_remaps_changed_indices():
    prev = [
        r"\begin{algorithmic}",
        r"\tfsegment{Init}",
        r"\State a",
        r"\tfsegment{Resp}",
        r"\State b",
        r"\end{algorithmic}",
    ]
    curr = [
        r"\begin{algorithmic}",
        r"\tfsegment{Init}",
        r"\State a",
        r"\tfsegment{Resp}",
        r"\State b2",
        r"\end{algorithmic}",
    ]
    # \State b2 is at original index 4 and changed
    cropped, changed = _apply_crop(curr, prev, {4})
    assert cropped == [
        r"\begin{algorithmic}",
        r"\tfsegmentstub{Init}",
        r"\State b2",
        r"\end{algorithmic}",
    ]
    assert changed == {2}  # \State b2 now at index 2


def _seg_lines(seg_a: str, seg_b: str) -> list[str]:
    """A 3-interior-segment algpseudocodex body: A, B, and final C."""
    return [
        r"\begin{algorithmic}",
        r"\tfsegment{A}",
        seg_a,
        r"\tfsegment{B}",
        seg_b,
        r"\tfsegment{C}",
        r"\State c",
        r"\end{algorithmic}",
    ]


def test_reduction_active_includes_related_pair_diff():
    """Regression for the reduction-panel crop bug: the related-game panels
    must be cropped to a set that includes the segment where the two related
    games differ (the hop), even when the reduction's own diff-vs-target set
    does not touch that segment. Otherwise the flanking clean panels either
    show a full listing or hide the hop."""
    games = {
        # G5 and G6 differ in segment A (index 1) -- the hop.
        "G5": _seg_lines(r"\State a", r"\State b"),
        "G6": _seg_lines(r"\State a2", r"\State b"),
        # Red differs from its diff target G6 only in segment B (index 2).
        "Red": _seg_lines(r"\State a2", r"\State b2"),
    }
    active = _reduction_active_segments(
        "Red", ["G5", "G6"], "G6", games.__getitem__,
    )
    # Segment 1 (G5 vs G6 hop) AND segment 2 (Red's own change) must both be
    # kept. The reduction's own diff-vs-G6 set alone would be just {2}.
    assert active == {1, 2}


def test_reduction_active_single_related_game():
    games = {
        "G4": _seg_lines(r"\State a", r"\State b"),
        "Red": _seg_lines(r"\State a", r"\State b2"),
    }
    active = _reduction_active_segments(
        "Red", ["G4"], "G4", games.__getitem__,
    )
    assert active == {2}


def test_html_tfsegmentstub_defined_for_each_profile():
    from texfrog.packages import get_profile
    for name in ("cryptocode", "nicodemus", "algpseudocodex"):
        assert r"\tfsegmentstub" in get_profile(name).html_tfsegmentstub()


# ---------------------------------------------------------------------------
# End-to-end compile of html_tfsegmentstub() inside each profile's env
# ---------------------------------------------------------------------------

# Each profile's minimal pseudocode environment, with a \tfsegmentstub{Foo}
# line typeset the way the real HTML pipeline would emit it (as one filtered
# content line, alongside one ordinary line). Regression coverage for the
# nicodemus \Statex bug: nicodemus is an \item-based list environment
# (enumitem via resources/nicodemus.sty) where \Statex is undefined, so the
# pre-fix html_tfsegmentstub() (which used \Statex unconditionally for any
# non-cryptocode profile) fails to compile here.
_STUB_GAME_BODIES = {
    "cryptocode": (
        r"\begin{pchstack}[boxed]" "\n"
        r"  \procedure{Test}{" "\n"
        r"    \tfsegmentstub{Foo}" "\n"
        r"    \pcreturn 1" "\n"
        r"  }" "\n"
        r"\end{pchstack}" "\n"
    ),
    "nicodemus": (
        r"\begin{nicodemus}" "\n"
        r"\tfsegmentstub{Foo}" "\n"
        r"\item $x \gets 1$" "\n"
        r"\end{nicodemus}" "\n"
    ),
    "algpseudocodex": (
        r"\begin{algorithmic}" "\n"
        r"\tfsegmentstub{Foo}" "\n"
        r"\State $x \gets 1$" "\n"
        r"\end{algorithmic}" "\n"
    ),
}


def _compile_profile_stub(
    tmp_path: Path, profile_name: str
) -> subprocess.CompletedProcess[str]:
    """Typeset ``\\tfsegmentstub{Foo}`` inside *profile_name*'s pseudocode
    environment, using the exact wrapper the real HTML pipeline builds
    (``_build_wrapper_template``), and compile it with pdflatex.
    """
    if profile_name == "nicodemus":
        # nicodemus.sty is not on CTAN; supply it locally like other
        # nicodemus-compiling tests do (see test_sty_compilation.py).
        shutil.copy2(_NICODEMUS_STY, tmp_path / "nicodemus.sty")

    wrapper_src = _build_wrapper_template(profile_name).format(
        macro_inputs="", gamename_defs="", game_file="game.tex"
    )
    (tmp_path / "wrapper.tex").write_text(wrapper_src, encoding="utf-8")
    (tmp_path / "game.tex").write_text(
        _STUB_GAME_BODIES[profile_name], encoding="utf-8"
    )

    return subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-no-shell-escape", "wrapper.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )


@needs_pdflatex
@pytest.mark.parametrize("profile_name", ["cryptocode", "nicodemus", "algpseudocodex"])
def test_html_tfsegmentstub_compiles_per_profile(tmp_path, profile_name):
    r"""\tfsegmentstub{...} from html_tfsegmentstub() must actually typeset
    (no undefined-control-sequence errors) inside each profile's pseudocode
    environment -- this is what the real HTML game-rendering pipeline
    (_compile_game_to_svg) does. Regression test for the nicodemus \Statex
    bug: \Statex is undefined in nicodemus's \item-based list environment.
    """
    result = _compile_profile_stub(tmp_path, profile_name)
    pdf = tmp_path / "wrapper.pdf"
    assert pdf.exists(), (
        f"pdflatex failed for profile {profile_name!r}.\n"
        f"Exit code: {result.returncode}\n"
        f"Log tail:\n{result.stdout[-3000:]}"
    )
    assert "Undefined control sequence" not in result.stdout
    assert "! " not in result.stdout, (
        f"pdflatex reported an error for profile {profile_name!r}:\n"
        f"{result.stdout[-3000:]}"
    )


# ---------------------------------------------------------------------------
# C1: \tfsegment markers must never leak into an UNCROPPED per-game render
# ---------------------------------------------------------------------------
#
# \tfsegment marker lines are only removed by crop_to_active_segments(). Any
# per-game .tex file that is NOT cropped -- crop off, game 0 (generate_html's
# `i == 0` check always skips _apply_crop, even when crop_default is on),
# and the -clean/-removed variants (never cropped) -- previously got the
# literal marker line verbatim. The HTML wrapper defines \tfsegmentstub but
# not \tfsegment, so pdflatex hit "Undefined control sequence" (still
# emitting a PDF under -interaction=nonstopmode) and the caption text leaked
# into the rendered SVG as a stray algorithm line.


@needs_html_tools
def test_generate_html_strips_tfsegment_markers_when_crop_off(tmp_path, capsys):
    r"""Full generate_html() pipeline, crop OFF, on a segmented source: no
    per-game .tex file may contain a literal \tfsegment marker, no compiled
    PDF may show the marker captions as stray text, and no compile log may
    report an undefined control sequence. Exercises game 0 specifically
    (the `i == 0` case that always skips cropping) since that's the game
    the underlying bug report called out."""
    games = [
        Game(label="G0", latex_name="G_0", description="Game 0",
             reduction=False, related_games=[]),
        Game(label="G1", latex_name="G_1", description="Game 1",
             reduction=False, related_games=[]),
    ]
    source_text = (
        r"\begin{algorithmic}[1]" "\n"
        r"\tfsegment{Setup phase}" "\n"
        r"\State $x \gets 0$" "\n"
        r"\tfsegment{Body phase}" "\n"
        r"\tfonly{G0}{\State $y \gets 0$}" "\n"
        r"\tfonly{G1}{\State $y \gets 1$}" "\n"
        r"\end{algorithmic}" "\n"
    )
    proof = Proof(
        source_name="test",
        macros=[],
        games=games,
        source_text=source_text,
        commentary={},
        figures=[],
        package="algpseudocodex",
        preamble=None,
        crop_default=False,  # crop OFF
    )

    out_dir = tmp_path / "html_out"
    generate_html(proof, tmp_path, out_dir, keep_tmp=True)

    captured = capsys.readouterr()
    m = re.search(r"Keeping intermediate files in (\S+)", captured.err)
    assert m, f"Could not find kept-tmp-dir path in stderr:\n{captured.err}"
    latex_dir = Path(m.group(1))

    # No per-game .tex file should contain a literal \tfsegment marker.
    for label in ("G0", "G1"):
        game_tex = (latex_dir / f"{label}.tex").read_text(encoding="utf-8")
        assert r"\tfsegment{" not in game_tex, (
            f"{label}.tex still contains a literal \\tfsegment marker "
            f"(crop is off, so it should have been stripped):\n{game_tex}"
        )

    # The compiled PDF (kept alongside the SVG under tmp_parent=latex_dir)
    # must show neither stray caption text nor an undefined-control-sequence
    # error -- game 0 in particular, since generate_html's `i == 0` check
    # always skips _apply_crop regardless of crop_default.
    for label in ("G0", "G1"):
        wrapper_pdf = latex_dir / label / "wrapper.pdf"
        assert wrapper_pdf.exists(), f"No compiled PDF kept for {label}"
        pdf_text = subprocess.run(
            ["pdftotext", str(wrapper_pdf), "-"],
            capture_output=True, text=True, timeout=30,
        ).stdout
        assert "Setup phase" not in pdf_text, (
            f"{label}'s compiled PDF leaks the \\tfsegment caption "
            f"'Setup phase' as stray text:\n{pdf_text}"
        )
        assert "Body phase" not in pdf_text, (
            f"{label}'s compiled PDF leaks the \\tfsegment caption "
            f"'Body phase' as stray text:\n{pdf_text}"
        )
        log_path = latex_dir / label / "wrapper.log"
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            assert "Undefined control sequence" not in log_text, (
                f"pdflatex reported an undefined control sequence for "
                f"{label} (likely \\tfsegment leaking to the wrapper):\n"
                f"{log_text[-3000:]}"
            )

    # The SVG must be a real render, not the build's error placeholder.
    svg_g0 = out_dir / "games" / "G0.svg"
    assert svg_g0.exists()
    svg_text = svg_g0.read_text(encoding="utf-8")
    assert "render failed" not in svg_text, (
        f"G0.svg is a render-failure placeholder:\n{svg_text}"
    )


# ---------------------------------------------------------------------------
# Issue #17: \tfrendergame diff= target must be honored in the HTML viewer,
# and the removed-panel file must be keyed by the successor (not the diff
# target), so a branch point that is the diff target of several games
# doesn't collide on a single "{target}-removed.svg" file.
# ---------------------------------------------------------------------------


@needs_html_tools
def test_generate_html_honors_branching_diff_target(tmp_path, capsys):
    r"""Family {G0, G1a, G1b} where both G1a and G1b branch off G0 (both set
    \tfrendergame[diff=G0]). Regression test for issue #17: without honoring
    diff_target, G1b's HTML diff target would default to its list
    predecessor G1a, and without keying removed-panel files by the
    successor, G1a's and G1b's "prev" panels would collide on a single
    G0-removed file."""
    games = [
        Game(label="G0", latex_name="G_0", description="Game 0",
             reduction=False, related_games=[]),
        Game(label="G1a", latex_name="G_{1a}", description="Branch A",
             reduction=False, related_games=[], diff_target="G0"),
        Game(label="G1b", latex_name="G_{1b}", description="Branch B",
             reduction=False, related_games=[], diff_target="G0"),
    ]
    source_text = (
        r"\begin{pcvstack}" "\n"
        r"common line \\" "\n"
        r"\tfonly{G0}{val-G0-only} \\" "\n"
        r"\tfonly{G1a}{val-G1a-only} \\" "\n"
        r"\tfonly{G1b}{val-G1b-only} \\" "\n"
        r"\end{pcvstack}" "\n"
    )
    proof = Proof(
        source_name="test",
        macros=[],
        games=games,
        source_text=source_text,
        commentary={},
        figures=[],
        package="cryptocode",
        preamble=None,
        crop_default=False,
    )

    out_dir = tmp_path / "html_out"
    generate_html(proof, tmp_path, out_dir, keep_tmp=True)

    captured = capsys.readouterr()
    m = re.search(r"Keeping intermediate files in (\S+)", captured.err)
    assert m, f"Could not find kept-tmp-dir path in stderr:\n{captured.err}"
    latex_dir = Path(m.group(1))

    # Both branches must get their own "prev" removed-highlight file, keyed
    # by the successor (G1a/G1b), not the shared diff target (G0) --
    # otherwise the second write silently clobbers the first.
    g1a_prev = (latex_dir / "G1a-prev-removed.tex").read_text(encoding="utf-8")
    g1b_prev = (latex_dir / "G1b-prev-removed.tex").read_text(encoding="utf-8")

    # Both panels show G0's content (the actual diff target), not G1a's --
    # the bug this regresses against would make G1b's panel show G1a's
    # content (its list predecessor) instead.
    for content, label in [(g1a_prev, "G1a"), (g1b_prev, "G1b")]:
        assert "val-G0-only" in content, (
            f"{label}-prev-removed.tex should show G0's content (the "
            f"explicit diff= target), got:\n{content}"
        )
        assert "val-G1a-only" not in content, (
            f"{label}-prev-removed.tex incorrectly shows G1a's content "
            f"instead of the diff target G0's:\n{content}"
        )
        assert "val-G1b-only" not in content, (
            f"{label}-prev-removed.tex incorrectly shows G1b's content "
            f"instead of the diff target G0's:\n{content}"
        )

    # Both compiled SVGs must exist as real renders (not error placeholders
    # and not one overwriting the other).
    for label in ("G1a", "G1b"):
        svg = out_dir / "games" / f"{label}-prev-removed.svg"
        assert svg.exists(), f"Missing {svg.name}"
        assert "render failed" not in svg.read_text(encoding="utf-8")

    # The manifest embedded in index.html must expose diff_target so app.js
    # can pick the correct panel instead of assuming list order.
    index_html = (out_dir / "index.html").read_text(encoding="utf-8")
    m_manifest = re.search(r"const GAMES = (\[.*?\]);", index_html, re.DOTALL)
    assert m_manifest, "Could not find GAMES manifest in index.html"
    manifest = json.loads(m_manifest.group(1))
    by_label = {g["label"]: g for g in manifest}
    assert by_label["G1a"]["diff_target"] == "G0"
    assert by_label["G1b"]["diff_target"] == "G0"


@needs_html_tools
def test_generate_html_crop_follows_diff_target_not_list_order(tmp_path, capsys):
    r"""Segment cropping must key off the resolved diff target, not list
    order. Family {G0, G1a, G1b}, both explicitly diff=G0, crop_default=True.
    G1a differs from G0 in the middle segment; G1b is textually identical to
    G0 everywhere. Cropped against the correct target (G0), G1b's changed
    segment is empty, so its only content-bearing segment gets stubbed away
    entirely. Cropped against the buggy list-order fallback (G1a, since G1a
    is G1b's immediate predecessor in \tfgames order), that segment would be
    (spuriously) marked active because G1a's own content differs from G1b's
    there -- the exact "rollback" failure mode from issue #17."""
    games = [
        Game(label="G0", latex_name="G_0", description="Game 0",
             reduction=False, related_games=[]),
        Game(label="G1a", latex_name="G_{1a}", description="Branch A",
             reduction=False, related_games=[], diff_target="G0"),
        Game(label="G1b", latex_name="G_{1b}", description="Branch B",
             reduction=False, related_games=[], diff_target="G0"),
    ]
    source_text = (
        r"\begin{algorithmic}[1]" "\n"
        r"\State opener-line" "\n"
        r"\tfsegment{Middle}" "\n"
        r"\tfonly{G0}{\State base-content}" "\n"
        r"\tfonly{G1a}{\State changed-content}" "\n"
        r"\tfonly{G1b}{\State base-content}" "\n"
        r"\tfsegment{Filler}" "\n"
        r"\State filler-content" "\n"
        r"\tfsegment{Closer}" "\n"
        r"\State closer-line" "\n"
        r"\end{algorithmic}" "\n"
    )
    proof = Proof(
        source_name="test",
        macros=[],
        games=games,
        source_text=source_text,
        commentary={},
        figures=[],
        package="algpseudocodex",
        preamble=None,
        crop_default=True,
    )

    out_dir = tmp_path / "html_out"
    generate_html(proof, tmp_path, out_dir, keep_tmp=True)

    captured = capsys.readouterr()
    m = re.search(r"Keeping intermediate files in (\S+)", captured.err)
    assert m, f"Could not find kept-tmp-dir path in stderr:\n{captured.err}"
    latex_dir = Path(m.group(1))

    g1a_tex = (latex_dir / "G1a.tex").read_text(encoding="utf-8")
    g1b_tex = (latex_dir / "G1b.tex").read_text(encoding="utf-8")

    # G1a truly differs from its target G0 in "Middle" -- that segment stays.
    assert "changed-content" in g1a_tex

    # G1b is textually identical to its target G0 everywhere, so "Middle"
    # (and "Filler") must be cropped away entirely -- if G1b's diff target
    # had fallen back to list order (G1a) instead of honoring diff=G0, this
    # segment would be spuriously kept/marked changed since G1a's content
    # differs from G1b's here.
    assert "base-content" not in g1b_tex, (
        f"G1b.tex should have cropped away its unchanged-vs-G0 'Middle' "
        f"segment, but found 'base-content' (spurious diff vs list "
        f"predecessor G1a instead of the real target G0):\n{g1b_tex}"
    )
    assert "filler-content" not in g1b_tex

    # The "prev" panel mirrors this: G1a's shows G0's real diff (kept),
    # G1b's shows no diff at all (stubbed).
    g1a_prev = (latex_dir / "G1a-prev-removed.tex").read_text(encoding="utf-8")
    g1b_prev = (latex_dir / "G1b-prev-removed.tex").read_text(encoding="utf-8")
    assert "base-content" in g1a_prev
    assert "base-content" not in g1b_prev


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
        # The opening line has unbalanced braces, so it should be skipped.
        assert result == _BUILTIN_MATHJAX_MACROS

    def test_skips_non_macro_lines(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            "% This is a comment\n"
            r"\usepackage{amsmath}" "\n"
            "some random text\n",
            encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        assert result == _BUILTIN_MATHJAX_MACROS

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
        assert result == _BUILTIN_MATHJAX_MACROS

    def test_empty_macros_list(self, tmp_path):
        result = _extract_mathjax_macros([], tmp_path)
        assert result == _BUILTIN_MATHJAX_MACROS

    def test_ensuremath_defined_even_with_no_user_macros(self, tmp_path):
        # Regression test: \tfdescription/\tfgamename content containing
        # \ensuremath{...} used to render as an "undefined control
        # sequence" error in the browser because MathJax has no built-in
        # \ensuremath, unlike real LaTeX.
        result = _extract_mathjax_macros([], tmp_path)
        assert r"\providecommand{\ensuremath}[1]{#1}" in result

    def test_ensuremath_still_defined_alongside_user_macros(self, tmp_path):
        macro_file = tmp_path / "macros.tex"
        macro_file.write_text(
            r"\newcommand{\foo}{bar}" "\n", encoding="utf-8",
        )
        result = _extract_mathjax_macros(["macros.tex"], tmp_path)
        assert r"\providecommand{\ensuremath}[1]{#1}" in result
        assert r"\newcommand{\foo}{bar}" in result


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
