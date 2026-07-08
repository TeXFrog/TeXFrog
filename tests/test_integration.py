"""Integration tests that invoke the CLI and compile LaTeX.

These tests run ``texfrog html build`` on the tutorial proofs exactly as
a user would, catching issues like package load order, missing macros,
and environment conflicts that unit tests cannot detect.

Skipped automatically when required external tools are not on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from texfrog.output.html import _find_svg_converter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The texfrog entrypoint lives next to the running Python interpreter.
TEXFROG = str(Path(sys.executable).parent / "texfrog")

# Tutorial directories to test (pure LaTeX .tex-based, main.tex entry point).
_TEX_TUTORIAL_NAMES = [
    "tutorial-cryptocode-quickstart",
    "tutorial-cryptocode",
    "tutorial-nicodemus",
]

# ---------------------------------------------------------------------------
# Skip markers
# ---------------------------------------------------------------------------

needs_pdflatex = pytest.mark.skipif(
    shutil.which("pdflatex") is None,
    reason="pdflatex not found on PATH",
)

needs_html_tools = pytest.mark.skipif(
    shutil.which("pdflatex") is None or _find_svg_converter() is None,
    reason="pdflatex and/or SVG converter (pdf2svg/pdftocairo) not on PATH",
)


def _assert_rendered_svg(svg: Path) -> None:
    """Assert *svg* is a real render, not the build's error placeholder.

    When pdflatex fails, ``texfrog html build`` writes a tiny placeholder SVG
    reading ``[SVG render failed for …]`` and still exits 0, so a size check
    alone (the placeholder is ~160 bytes) does not catch a broken build.
    """
    assert svg.exists(), f"SVG not produced for {svg.stem}"
    content = svg.read_text(encoding="utf-8")
    assert "render failed" not in content, (
        f"{svg.name} is a render-failure placeholder, not a real render:\n{content}"
    )
    assert svg.stat().st_size > 100, f"SVG suspiciously small for {svg.stem}"


def test_assert_rendered_svg_rejects_placeholder(tmp_path):
    """The SVG guard must reject the build's render-failure placeholder."""
    placeholder = tmp_path / "G0.svg"
    placeholder.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60">'
        '<text x="10" y="40">[SVG render failed for G0]</text></svg>'
    )
    with pytest.raises(AssertionError, match="render-failure placeholder"):
        _assert_rendered_svg(placeholder)


# ---------------------------------------------------------------------------
# texfrog html build (pure LaTeX .tex-based tutorials)
# ---------------------------------------------------------------------------


@needs_html_tools
@pytest.mark.parametrize("tutorial_name", _TEX_TUTORIAL_NAMES)
def test_texfrog_html_build_tex(tmp_path, tutorial_name):
    """``texfrog html build`` produces a complete site with SVGs (.tex input)."""
    from texfrog.tex_parser import parse_tex_proof

    tutorial_dir = _PROJECT_ROOT / "examples" / tutorial_name
    tex_path = tutorial_dir / "main.tex"
    proof = parse_tex_proof(tex_path)
    game_labels = [g.label for g in proof.games]

    out = tmp_path / "html"

    result = subprocess.run(
        [TEXFROG, "html", "build", str(tex_path), "-o", str(out)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"texfrog html build failed:\n{result.stderr}"

    # Site scaffolding.
    assert (out / "index.html").exists()
    assert (out / "style.css").exists()
    assert (out / "app.js").exists()

    # Every game should have a real (non-placeholder) SVG.
    games_dir = out / "games"
    for label in game_labels:
        _assert_rendered_svg(games_dir / f"{label}.svg")


@needs_html_tools
@pytest.mark.parametrize("package", ["cryptocode", "nicodemus"])
def test_texfrog_init_then_html_build(tmp_path, package):
    """``texfrog init`` followed by ``texfrog html build`` produces a working site."""
    from texfrog.tex_parser import parse_tex_proof

    init_dir = tmp_path / "proof"
    result = subprocess.run(
        [TEXFROG, "init", str(init_dir), "--package", package],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"texfrog init failed:\n{result.stderr}"

    tex_path = init_dir / "proof.tex"
    assert tex_path.exists(), "texfrog init did not create proof.tex"

    proof = parse_tex_proof(tex_path)
    game_labels = [g.label for g in proof.games]

    out = tmp_path / "html"
    result = subprocess.run(
        [TEXFROG, "html", "build", str(tex_path), "-o", str(out)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"texfrog html build failed:\n{result.stderr}"

    assert (out / "index.html").exists()
    games_dir = out / "games"
    for label in game_labels:
        _assert_rendered_svg(games_dir / f"{label}.svg")


@needs_html_tools
def test_texfrog_html_build_multiproof(tmp_path):
    """``texfrog html build`` on a multi-proof document creates per-proof subdirectories."""
    from texfrog.tex_parser import parse_tex_proofs

    tex_path = _PROJECT_ROOT / "examples" / "example-multiproof" / "main.tex"
    if not tex_path.exists():
        pytest.skip("examples/example-multiproof not found")

    proofs = parse_tex_proofs(tex_path)
    assert len(proofs) == 2

    out = tmp_path / "html"

    result = subprocess.run(
        [TEXFROG, "html", "build", str(tex_path), "-o", str(out)],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, f"texfrog html build failed:\n{result.stderr}"

    # Top-level index page should exist.
    assert (out / "index.html").exists()
    index_html = (out / "index.html").read_text(encoding="utf-8")
    assert "indcpa" in index_html
    assert "intctxt" in index_html

    # Each proof should have its own subdirectory with full site scaffolding.
    for proof in proofs:
        proof_dir = out / proof.source_name
        assert (proof_dir / "index.html").exists(), f"Missing index.html for {proof.source_name}"
        assert (proof_dir / "style.css").exists(), f"Missing style.css for {proof.source_name}"
        assert (proof_dir / "app.js").exists(), f"Missing app.js for {proof.source_name}"

        # Every game should have a non-empty SVG.
        games_dir = proof_dir / "games"
        for game in proof.games:
            svg = games_dir / f"{game.label}.svg"
            assert svg.exists(), f"SVG not produced for {proof.source_name}/{game.label}"
            assert svg.stat().st_size > 100, f"SVG suspiciously small for {proof.source_name}/{game.label}"
