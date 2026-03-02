"""Integration tests that invoke the CLI and compile LaTeX.

These tests run ``texfrog latex`` and ``texfrog html build`` on the
tutorial proof exactly as a user would, catching issues like package
load order, missing macros, and environment conflicts that unit tests
cannot detect.

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
TUTORIAL_DIR = _PROJECT_ROOT / "tutorial"
TUTORIAL_YAML = TUTORIAL_DIR / "proof.yaml"
TUTORIAL_MAIN_TEX = TUTORIAL_DIR / "texfrog_latex" / "main.tex"

# The texfrog entrypoint lives next to the running Python interpreter.
TEXFROG = str(Path(sys.executable).parent / "texfrog")

# Game labels defined in tutorial/proof.yaml.
TUTORIAL_GAMES = ["G0", "G1", "Red1", "G2"]

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
# texfrog latex
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_texfrog_latex(tmp_path):
    """``texfrog latex`` generates files and pdflatex compiles them."""
    out = tmp_path / "latex"

    # 1. Run the CLI command.
    result = subprocess.run(
        [TEXFROG, "latex", str(TUTORIAL_YAML), "-o", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"texfrog latex failed:\n{result.stderr}"

    # 2. Check expected output files exist.
    assert (out / "proof_harness.tex").exists()
    for label in TUTORIAL_GAMES:
        assert (out / f"{label}.tex").exists()
    assert (out / "fig_all_games.tex").exists()

    # 3. Copy the standalone main.tex into the output dir and compile.
    shutil.copy2(TUTORIAL_MAIN_TEX, out / "main.tex")
    shutil.copy2(TUTORIAL_DIR / "macros.tex", out / "macros.tex")
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "main.tex"],
        cwd=out, capture_output=True, text=True,
    )
    assert (out / "main.pdf").exists(), (
        f"pdflatex failed on main.tex:\n{result.stdout[-3000:]}"
    )


# ---------------------------------------------------------------------------
# texfrog html build
# ---------------------------------------------------------------------------


@needs_html_tools
def test_texfrog_html_build(tmp_path):
    """``texfrog html build`` produces a complete site with SVGs."""
    out = tmp_path / "html"

    result = subprocess.run(
        [TEXFROG, "html", "build", str(TUTORIAL_YAML), "-o", str(out)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"texfrog html build failed:\n{result.stderr}"

    # Site scaffolding.
    assert (out / "index.html").exists()
    assert (out / "style.css").exists()
    assert (out / "app.js").exists()

    # Every game should have a non-empty SVG.
    games_dir = out / "games"
    for label in TUTORIAL_GAMES:
        svg = games_dir / f"{label}.svg"
        assert svg.exists(), f"SVG not produced for {label}"
        assert svg.stat().st_size > 100, f"SVG suspiciously small for {label}"
