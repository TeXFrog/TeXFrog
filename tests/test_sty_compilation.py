"""Tests that compile LaTeX documents using texfrog.sty with pdflatex.

These tests verify that the texfrog.sty LaTeX package correctly compiles
documents using various TeXFrog commands.  Each test writes a minimal .tex
document to a temp directory, copies texfrog.sty alongside it, and runs
pdflatex.

Skipped automatically when pdflatex is not on PATH.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_STY_PATH = _PROJECT_ROOT / "latex" / "texfrog.sty"
_TUTORIAL_DIR = _PROJECT_ROOT / "examples" / "tutorial-pure-latex"

needs_pdflatex = pytest.mark.skipif(
    shutil.which("pdflatex") is None,
    reason="pdflatex not found on PATH",
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _compile_tex(
    tmp_path: Path,
    tex_content: str,
    *,
    extra_files: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Write a .tex document and compile it with pdflatex.

    Copies texfrog.sty into *tmp_path*, writes ``test.tex`` with the given
    content, and runs pdflatex.

    Args:
        tmp_path: Temporary directory for compilation.
        tex_content: Full LaTeX document source.
        extra_files: Optional mapping of filename -> content to write
            alongside the .tex file (e.g. macro files).

    Returns:
        The completed subprocess result.
    """
    shutil.copy2(_STY_PATH, tmp_path / "texfrog.sty")
    (tmp_path / "test.tex").write_text(tex_content, encoding="utf-8")
    if extra_files:
        for name, content in extra_files.items():
            (tmp_path / name).write_text(content, encoding="utf-8")
    return subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-no-shell-escape", "test.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _assert_compiled(tmp_path: Path, result: subprocess.CompletedProcess[str]) -> None:
    """Assert that pdflatex produced a PDF successfully."""
    pdf = tmp_path / "test.pdf"
    assert pdf.exists(), (
        f"pdflatex did not produce test.pdf.\n"
        f"Exit code: {result.returncode}\n"
        f"Log tail:\n{result.stdout[-3000:]}"
    )


# ---------------------------------------------------------------------------
# Minimal preamble used by most synthetic tests
# ---------------------------------------------------------------------------

_CRYPTO_PREAMBLE = r"""\documentclass{article}
\usepackage[n,advantage,operators,sets,adversary,landau,probability,notions,logic,ff,mm,primitives,events,complexity,oracles,asymptotics,keys]{cryptocode}
\usepackage{texfrog}
"""


# ---------------------------------------------------------------------------
# Full tutorial compilation
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tutorial_pure_latex_compiles(tmp_path):
    """The tutorial-pure-latex/main.tex compiles with pdflatex."""
    # Copy the entire tutorial directory so macros.tex is found.
    tutorial_copy = tmp_path / "tutorial"
    shutil.copytree(_TUTORIAL_DIR, tutorial_copy)
    shutil.copy2(_STY_PATH, tutorial_copy / "texfrog.sty")

    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-no-shell-escape", "main.tex"],
        cwd=tutorial_copy,
        capture_output=True,
        text=True,
        timeout=120,
    )
    pdf = tutorial_copy / "main.pdf"
    assert pdf.exists(), (
        f"pdflatex failed on tutorial main.tex.\n"
        f"Exit code: {result.returncode}\n"
        f"Log tail:\n{result.stdout[-3000:]}"
    )


# ---------------------------------------------------------------------------
# Basic game registration and rendering
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_basic_two_game_proof(tmp_path):
    r"""A minimal 2-game proof with \tfgames, \tfgamename, \tfrendergame."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, G1}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}
\tfsetpackage{cryptocode}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{$\tfgamename{G0}$}{
    \tfonly{G0}{x \gets 0 \\}
    \tfonly{G1}{x \gets 1 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\tfrendergame{test}{G1}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tfonly with range syntax
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tfonly_range_syntax(tmp_path):
    r"""\tfonly{G0-G2}{...} range syntax resolves correctly."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, G1, G2}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}
\tfgamename{G2}{G_2}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{Game}{
    \tfonly{G0-G2}{x \gets 0 \\}
    \tfonly{G2}{y \gets 1 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\tfrendergame{test}{G1}
\tfrendergame{test}{G2}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tfonly* (star variant — suppressed in figures)
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tfonly_star_variant(tmp_path):
    r"""\tfonly*{tags}{content} renders in games but is suppressed in figures."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, G1}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{%
    \tfonly*{G0}{Game $\tfgamename{G0}$}%
    \tfonly*{G1}{Game $\tfgamename{G1}$}%
  }{
    \tfonly{G0}{x \gets 0 \\}
    \tfonly{G1}{x \gets 1 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\tfrendergame{test}{G1}
\tfrenderfigure{test}{G0,G1}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tffigonly — content only in figures
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tffigonly(tmp_path):
    r"""\tffigonly{content} appears only in \tfrenderfigure output."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, G1}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{%
    \tfonly*{G0}{Game $\tfgamename{G0}$}%
    \tfonly*{G1}{Game $\tfgamename{G1}$}%
    \tffigonly{Games $\tfgamename{G0}$--$\tfgamename{G1}$}%
  }{
    \tfonly{G0}{x \gets 0 \\}
    \tfonly{G1}{x \gets 1 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\tfrenderfigure{test}{G0,G1}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tfrenderfigure — consolidated multi-game figure
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_renderfigure_multi_game(tmp_path):
    r"""\tfrenderfigure with multiple games compiles."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, G1, G2}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}
\tfgamename{G2}{G_2}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{Game}{
    \tfonly{G0}{x \gets 0 \\}
    \tfonly{G1}{x \gets 1 \\}
    \tfonly{G2}{x \gets 2 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrenderfigure{test}{G0,G1,G2}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tfrendergame[highlight=false] — clean mode
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_rendergame_no_highlight(tmp_path):
    r"""\tfrendergame[highlight=false] compiles without highlighting."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, G1}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{Game}{
    \tfonly{G0}{x \gets 0 \\}
    \tfonly{G1}{x \gets 1 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame[highlight=false]{test}{G1}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# Reductions
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_reduction_rendering(tmp_path):
    r"""\tfreduction + \tfrelatedgames + rendering a reduction game."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, Red, G1}
\tfgamename{G0}{G_0}
\tfgamename{Red}{\mathcal{B}}
\tfgamename{G1}{G_1}
\tfreduction{Red}
\tfrelatedgames{Red}{G0, G1}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{Game}{
    \tfonly{G0}{x \gets 0 \\}
    \tfonly{Red}{x \gets \mathcal{O}(0) \\}
    \tfonly{G1}{x \gets 1 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\tfrendergame{test}{Red}
\tfrendergame{test}{G1}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tfcommentary, \tfdescription — no-ops in LaTeX, must not error
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_commentary_and_description_noop(tmp_path):
    r"""\tfcommentary and \tfdescription are no-ops but must not cause errors."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, G1}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}
\tfdescription{G0}{Starting game.}
\tfdescription{G1}{Modified game.}
\tfcommentary{G1}{This is a transition argument.}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{Game}{
    \tfonly{G0}{x \gets 0 \\}
    \tfonly{G1}{x \gets 1 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\tfrendergame{test}{G1}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tfpreamble — no-op in LaTeX
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tfpreamble_noop(tmp_path):
    r"""\tfpreamble is a no-op but must not cause errors."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0}
\tfgamename{G0}{G_0}
\tfpreamble{preamble.tex}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{Game}{
    \pcreturn 0
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tfmacrofile + \input of user macros
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_user_macro_file(tmp_path):
    r"""User macro files loaded via \input work alongside texfrog.sty."""
    tex = _CRYPTO_PREAMBLE + r"""
\input{mymacros.tex}
\tfgames{G0}
\tfgamename{G0}{G_0}
\tfmacrofile{mymacros.tex}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{Game}{
    x \gets \myfunc(0) \\
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\end{document}
"""
    result = _compile_tex(
        tmp_path, tex,
        extra_files={"mymacros.tex": r"\newcommand{\myfunc}{\mathsf{F}}"},
    )
    _assert_compiled(tmp_path, result)


# ---------------------------------------------------------------------------
# \tffigure — no-op in LaTeX
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tffigure_noop(tmp_path):
    r"""\tffigure is a no-op but must not cause errors."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{G0, G1}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}
\tffigure{indcpa}{G0,G1}

\begin{tfsource}{test}
\begin{pchstack}[boxed]
  \procedure{Game}{
    \tfonly{G0}{x \gets 0 \\}
    \tfonly{G1}{x \gets 1 \\}
    \pcreturn x
  }
\end{pchstack}
\end{tfsource}

\begin{document}
\tfrendergame{test}{G0}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)
