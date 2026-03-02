"""Integration tests that invoke the CLI and compile LaTeX.

These tests run ``texfrog latex`` and ``texfrog html build`` on the
tutorial proofs exactly as a user would, catching issues like package
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
from texfrog.parser import parse_proof

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The texfrog entrypoint lives next to the running Python interpreter.
TEXFROG = str(Path(sys.executable).parent / "texfrog")

# Tutorial directories to test.  Add new entries here as tutorials are created.
_TUTORIAL_NAMES = ["tutorial", "tutorial-nicodemus"]

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
@pytest.mark.parametrize("tutorial_name", _TUTORIAL_NAMES)
def test_texfrog_latex(tmp_path, tutorial_name):
    """``texfrog latex`` generates files and pdflatex compiles them."""
    tutorial_dir = _PROJECT_ROOT / tutorial_name
    yaml_path = tutorial_dir / "proof.yaml"
    proof = parse_proof(yaml_path)
    game_labels = [g.label for g in proof.games]

    out = tmp_path / "latex"

    # 1. Run the CLI command.
    result = subprocess.run(
        [TEXFROG, "latex", str(yaml_path), "-o", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"texfrog latex failed:\n{result.stderr}"

    # 2. Check expected output files exist.
    assert (out / "proof_harness.tex").exists()
    for label in game_labels:
        assert (out / f"{label}.tex").exists()
    for figure in proof.figures:
        assert (out / f"fig_{figure.label}.tex").exists()

    # 3. Copy the standalone main.tex and macro files into the output dir.
    main_tex = tutorial_dir / "main.tex"
    shutil.copy2(main_tex, out / "main.tex")
    for macro_file in proof.macros:
        src = tutorial_dir / macro_file
        shutil.copy2(src, out / Path(macro_file).name)

    # 4. Compile with pdflatex.
    result = subprocess.run(
        ["pdflatex", "main.tex"],
        cwd=out, capture_output=True, text=True,
    )
    assert (out / "main.pdf").exists(), (
        f"pdflatex failed on main.tex:\n{result.stdout[-3000:]}"
    )


# ---------------------------------------------------------------------------
# texfrog html build
# ---------------------------------------------------------------------------


@needs_html_tools
@pytest.mark.parametrize("tutorial_name", _TUTORIAL_NAMES)
def test_texfrog_html_build(tmp_path, tutorial_name):
    """``texfrog html build`` produces a complete site with SVGs."""
    tutorial_dir = _PROJECT_ROOT / tutorial_name
    yaml_path = tutorial_dir / "proof.yaml"
    proof = parse_proof(yaml_path)
    game_labels = [g.label for g in proof.games]

    out = tmp_path / "html"

    result = subprocess.run(
        [TEXFROG, "html", "build", str(yaml_path), "-o", str(out)],
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
