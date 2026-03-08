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

    # Every game should have a non-empty SVG.
    games_dir = out / "games"
    for label in game_labels:
        svg = games_dir / f"{label}.svg"
        assert svg.exists(), f"SVG not produced for {label}"
        assert svg.stat().st_size > 100, f"SVG suspiciously small for {label}"


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
