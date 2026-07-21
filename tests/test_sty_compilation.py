"""Tests that compile LaTeX documents using texfrog.sty with pdflatex.

These tests verify that the texfrog.sty LaTeX package correctly compiles
documents using various TeXFrog commands.  Each test writes a minimal .tex
document to a temp directory, copies texfrog.sty alongside it, and runs
pdflatex.

Skipped automatically when pdflatex is not on PATH.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_STY_PATH = _PROJECT_ROOT / "latex" / "texfrog.sty"
_TUTORIAL_DIR = _PROJECT_ROOT / "examples" / "tutorial-cryptocode-quickstart"

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


def _pdftotext(tmp_path: Path) -> str:
    """Extract plain text from the compiled ``test.pdf`` via ``pdftotext``."""
    return subprocess.run(
        ["pdftotext", str(tmp_path / "test.pdf"), "-"],
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout


def _pdftotext_layout(tmp_path: Path) -> str:
    """Like :func:`_pdftotext` but preserves horizontal layout (``-layout``).

    Needed to check that a line number stays on the same physical line as its
    statement's content (vertical alignment is lost without ``-layout``).
    """
    return subprocess.run(
        ["pdftotext", "-layout", str(tmp_path / "test.pdf"), "-"],
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout


# ---------------------------------------------------------------------------
# Minimal preamble used by most synthetic tests
# ---------------------------------------------------------------------------

_CRYPTO_PREAMBLE = r"""\documentclass{article}
\usepackage[n,advantage,operators,sets,adversary,landau,probability,notions,logic,ff,mm,primitives,events,complexity,oracles,asymptotics,keys]{cryptocode}
\usepackage[package=cryptocode]{texfrog}
"""

_ALGPSEUDOCODEX_PREAMBLE = r"""\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage{algpseudocodex}
\usepackage[package=algpseudocodex]{texfrog}
"""

_NICODEMUS_PREAMBLE = r"""\documentclass{article}
\usepackage[margin=1in,letterpaper]{geometry}
\usepackage{amsfonts,amsmath,amsthm}
\usepackage{xcolor}
\usepackage{nicodemus}
\usepackage[package=nicodemus]{texfrog}
"""

_NICODEMUS_STY_PATH = _PROJECT_ROOT / "resources" / "nicodemus.sty"


# ---------------------------------------------------------------------------
# Full tutorial compilation
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tutorial_cryptocode_quickstart_compiles(tmp_path):
    """The tutorial-cryptocode-quickstart/main.tex compiles with pdflatex."""
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
\tfgames{test}{G0, G1}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}

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
\tfrendergame[diff=G0]{test}{G1}
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
\tfgames{test}{G0, G1, G2}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}
\tfgamename{test}{G2}{G_2}

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
\tfgames{test}{G0, G1}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}

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
\tfgames{test}{G0, G1}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}

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
\tfgames{test}{G0, G1, G2}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}
\tfgamename{test}{G2}{G_2}

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


@needs_pdflatex
def test_algpseudocodex_package_option(tmp_path):
    r"""package=algpseudocodex is accepted and \tfgamelabel uses \Comment."""
    tex = _ALGPSEUDOCODEX_PREAMBLE + r"""
\tfgames{test}{G0, G1, G2}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}
\tfgamename{test}{G2}{G_2}

\begin{tfsource}{test}
\begin{algorithmic}[1]
\Procedure{Game}{}
\tfonly{G0}{\State $x \gets 0$}
\tfonly{G1}{\State $x \gets 1$}
\tfonly{G2}{\State $x \gets 2$}
\State \Return $x$
\EndProcedure
\end{algorithmic}
\end{tfsource}

\begin{document}
\tfrenderfigure{test}{G0,G1,G2}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)
    # pdflatex -interaction=nonstopmode still writes a PDF after an undefined
    # control sequence (it skips the token and continues), so _assert_compiled
    # alone can't tell "compiled cleanly" from "compiled with swallowed
    # errors" — check the log directly to guard against the fallback-to-
    # cryptocode bug this test exists to catch.
    assert "Undefined control sequence" not in result.stdout, (
        f"pdflatex reported undefined control sequences despite producing a "
        f"PDF (package=algpseudocodex may have fallen back to cryptocode's "
        f"\\pccomment).\nLog tail:\n{result.stdout[-3000:]}"
    )


@needs_pdflatex
def test_unknown_package_option_warns_and_falls_back(tmp_path):
    r"""An invalid package= value emits a clear texfrog warning (naming the
    valid choices) and falls back to cryptocode, instead of failing silently
    or with l3keys' generic "accepts only a fixed set of choices" error.
    """
    tex = r"""\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage[package=bogus]{texfrog}
\begin{document}
hi
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)
    error_lines = [
        line for line in result.stdout.splitlines() if line.startswith("!")
    ]
    assert not error_lines, (
        f"pdflatex reported errors for an invalid package= value: {error_lines}\n"
        f"Log tail:\n{result.stdout[-3000:]}"
    )
    assert "texfrog Warning" in result.stdout
    assert "cryptocode, nicodemus, algpseudocodex" in " ".join(
        result.stdout.split()
    )


# ---------------------------------------------------------------------------
# \tfrendergame default (no highlighting) and \tfrendergame[diff=...] (with highlighting)
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_rendergame_no_highlight_by_default(tmp_path):
    r"""\tfrendergame without options compiles without highlighting."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{test}{G0, G1}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}

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
\tfrendergame{test}{G1}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    _assert_compiled(tmp_path, result)


@needs_pdflatex
def test_rendergame_diff_explicit_target(tmp_path):
    r"""\tfrendergame[diff=G0] compiles with highlighting against G0."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{test}{G0, G1}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}

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
\tfrendergame[diff=G0]{test}{G1}
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
\tfgames{test}{G0, Red, G1}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{Red}{\mathcal{B}}
\tfgamename{test}{G1}{G_1}
\tfreduction{test}{Red}
\tfrelatedgames{test}{Red}{G0, G1}

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
\tfrendergame[diff=G0]{test}{Red}
\tfrendergame[diff=G0]{test}{G1}
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
\tfgames{test}{G0, G1}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}
\tfdescription{test}{G0}{Starting game.}
\tfdescription{test}{G1}{Modified game.}
\tfcommentary{test}{G1}{This is a transition argument.}

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
\tfgames{test}{G0}
\tfgamename{test}{G0}{G_0}
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
\tfgames{test}{G0}
\tfgamename{test}{G0}{G_0}
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
# texfrog init round-trip: scaffold → pdflatex
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_init_cryptocode_proof_compiles(tmp_path):
    """Scaffolded cryptocode proof.tex compiles with pdflatex."""
    from click.testing import CliRunner
    from texfrog.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0

    shutil.copy2(_STY_PATH, tmp_path / "texfrog.sty")

    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-no-shell-escape", "proof.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    pdf = tmp_path / "proof.pdf"
    assert pdf.exists(), (
        f"pdflatex failed on scaffolded proof.tex.\n"
        f"Exit code: {result.returncode}\n"
        f"Log tail:\n{result.stdout[-3000:]}"
    )


@needs_pdflatex
def test_init_nicodemus_proof_compiles(tmp_path):
    """Scaffolded nicodemus proof.tex compiles with pdflatex.

    ``texfrog init --package nicodemus`` bundles ``nicodemus.sty`` (it is not
    on CTAN), so only ``texfrog.sty`` needs to be supplied here.
    """
    from click.testing import CliRunner
    from texfrog.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path), "--package", "nicodemus"])
    assert result.exit_code == 0

    shutil.copy2(_STY_PATH, tmp_path / "texfrog.sty")

    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-no-shell-escape", "proof.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    pdf = tmp_path / "proof.pdf"
    assert pdf.exists(), (
        f"pdflatex failed on scaffolded nicodemus proof.tex.\n"
        f"Exit code: {result.returncode}\n"
        f"Log tail:\n{result.stdout[-3000:]}"
    )


@needs_pdflatex
def test_init_algpseudocodex_proof_compiles(tmp_path):
    """Scaffolded algpseudocodex proof.tex compiles with pdflatex."""
    from click.testing import CliRunner
    from texfrog.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path), "--package", "algpseudocodex"])
    assert result.exit_code == 0

    shutil.copy2(_STY_PATH, tmp_path / "texfrog.sty")

    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-no-shell-escape", "proof.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    pdf = tmp_path / "proof.pdf"
    assert pdf.exists(), (
        f"pdflatex failed on scaffolded algpseudocodex proof.tex.\n"
        f"Exit code: {result.returncode}\n"
        f"Log tail:\n{result.stdout[-3000:]}"
    )
    # pdflatex -interaction=nonstopmode still writes a PDF after LaTeX
    # errors (it recovers and continues), so pdf.exists() alone can't catch
    # a broken \tfrendergame[diff=...] highlighted render — check the log
    # directly. This is exactly the failure mode a naive \tfchanged wrap of
    # a whole \State line produces for algorithmicx-style packages.
    error_lines = [
        line for line in result.stdout.splitlines() if line.startswith("!")
    ]
    assert not error_lines, (
        f"pdflatex reported errors despite producing a PDF: {error_lines}\n"
        f"Log tail:\n{result.stdout[-3000:]}"
    )


# ---------------------------------------------------------------------------
# \tffigure — no-op in LaTeX
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tffigure_noop(tmp_path):
    r"""\tffigure is a no-op but must not cause errors."""
    tex = _CRYPTO_PREAMBLE + r"""
\tfgames{test}{G0, G1}
\tfgamename{test}{G0}{G_0}
\tfgamename{test}{G1}{G_1}
\tffigure{test}{fig1}{G0,G1}

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


# ---------------------------------------------------------------------------
# \tfsegment — scaffolding, must be invisible in existing (non-crop) modes
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_tfsegment_invisible_in_full_render(tmp_path):
    r"""\tfsegment must not change full-render output (crop is off by default
    and nothing sets \g__tf_crop_active_bool yet -- that lands in Task 6)."""
    tex = _ALGPSEUDOCODEX_PREAMBLE + r"""
\tfgames{s}{G0,G1}
\tfgamename{s}{G0}{G_0}\tfgamename{s}{G1}{G_1}
\begin{tfsource}{s}
\begin{algorithmic}[1]
\State \(x \gets 0\)
\tfsegment{Second}
\tfonly{G1}{\State \(y \gets 1\)}
\end{algorithmic}
\end{tfsource}
\begin{document}
\tfrendergame{s}{G0}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    # \tfsegment must not leak literal text into the PDF/log as an error
    assert "Undefined control sequence" not in result.stdout


@needs_pdflatex
def test_tfsegmentstub_defined_for_algpseudocodex(tmp_path):
    r"""\tfsegmentstub must have a working default under package=algpseudocodex
    (the profile Task 6's crop render actually exercises). Regression test for
    a bug where the base \providecommand was nested inside the cryptocode/
    nicodemus \tl_if_eq:NnT override blocks, leaving \tfsegmentstub entirely
    undefined for algpseudocodex."""
    tex = _ALGPSEUDOCODEX_PREAMBLE + r"""
\begin{document}
\begin{algorithmic}[1]
\tfsegmentstub{Foo}
\end{algorithmic}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    assert "Undefined control sequence" not in result.stdout


# ---------------------------------------------------------------------------
# I3: \tfsegmentstub's \color{black!55} must be grouped in the cryptocode
# and nicodemus overrides (matching the base algpseudocodex definition),
# so it doesn't leak past the stub and gray out every subsequent line.
# ---------------------------------------------------------------------------

# Static source check: a leaked \color still compiles fine (pdflatex has no
# way to know "this shade of gray was supposed to be scoped"), so a
# compile-only test would not have caught the original ungrouped-color bug.
# This regex directly targets the shape of the fix: \color{black!55} must
# sit inside its own brace group within each override's \tfsegmentstub body.
_CRYPTOCODE_STUB_GROUPED_RE = re.compile(
    r"\\cs_gset_protected:Npn\s*\\tfsegmentstub\s*#1\s*"
    r"\{\s*"
    r"\{\\color\{black!55\}.*?\\ensuremath\{\\cdots\}\}\s*"
    r"\\\\\s*"
    r"\}",
    re.DOTALL,
)
_NICODEMUS_STUB_GROUPED_RE = re.compile(
    r"\\cs_gset_protected:Npn\s*\\tfsegmentstub\s*#1\s*"
    r"\{\s*"
    r"\\item\s*\{\\color\{black!55\}.*?\\ensuremath\{\\cdots\}\}\s*"
    r"\}",
    re.DOTALL,
)


def test_tfsegmentstub_color_is_grouped_for_cryptocode_and_nicodemus():
    r"""I3 regression: the cryptocode and nicodemus \tfsegmentstub overrides
    must wrap \color{black!55} in a brace group, exactly like the base
    algpseudocodex definition (\Statex{\color{black!55}...}). Before the
    fix, both overrides applied \color{black!55} UNGROUPED, so it kept
    coloring every sibling line rendered after the stub gray instead of
    just the stub's own text -- a silent visual bug pdflatex's exit code
    can't detect (see the compile tests below for the "still typesets"
    half of this regression test)."""
    sty_text = _STY_PATH.read_text(encoding="utf-8")
    assert _CRYPTOCODE_STUB_GROUPED_RE.search(sty_text), (
        "cryptocode's \\tfsegmentstub override must wrap \\color{black!55} "
        "in its own brace group ({\\color{black!55}...}) with the trailing "
        "\\\\ outside the group."
    )
    assert _NICODEMUS_STUB_GROUPED_RE.search(sty_text), (
        "nicodemus's \\tfsegmentstub override must wrap \\color{black!55} "
        "in its own brace group ({\\color{black!55}...}) with \\item "
        "outside the group."
    )


@needs_pdflatex
def test_tfsegmentstub_grouped_color_compiles_cryptocode(tmp_path):
    r"""The grouped \tfsegmentstub form must still typeset correctly for
    cryptocode: a stub followed by more procedure content on the same
    brace level (the actual usage pattern -- see
    \__tf_seg_render_one:n) must compile without errors, and the \\
    line-separator placed outside the group must still terminate the
    line correctly."""
    tex = _CRYPTO_PREAMBLE + r"""
\begin{document}
\begin{pchstack}[boxed]
  \procedure{Game}{
    \tfsegmentstub{Foo}
    x \gets 0 \\
    \pcreturn x
  }
\end{pchstack}
\end{document}
"""
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    assert "Undefined control sequence" not in result.stdout
    text = _pdftotext(tmp_path)
    assert "unchanged" in text
    assert "Foo" in text


@needs_pdflatex
def test_tfsegmentstub_grouped_color_compiles_nicodemus(tmp_path):
    r"""The grouped \tfsegmentstub form must still typeset correctly for
    nicodemus: a stub followed by more \item lines on the same brace level
    must compile without errors, and the \item placed outside the group
    must still produce a proper list entry."""
    tex = _NICODEMUS_PREAMBLE + r"""
\begin{document}
\begin{nicodemus}
\tfsegmentstub{Foo}
\item $x \gets 0$
\end{nicodemus}
\end{document}
"""
    result = _compile_tex(
        tmp_path, tex,
        extra_files={"nicodemus.sty": _NICODEMUS_STY_PATH.read_text(encoding="utf-8")},
    )
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    assert "Undefined control sequence" not in result.stdout
    text = _pdftotext(tmp_path)
    assert "unchanged" in text
    assert "Foo" in text


# ---------------------------------------------------------------------------
# Task 6: crop-aware render pass
# ---------------------------------------------------------------------------

# Shared fixture body for the crop tests below: segment 0 (before the first
# \tfsegment) holds the \begin{algorithmic} opener; "Initiator" is an
# interior segment whose content is NOT \tfonly-tagged, so it never differs
# between G0 and G1 (unchanged); "Responder" is the final segment (holds
# \end{algorithmic}) and its \tfonly-gated line differs between G0 and G1
# (changed).
_CROP_SOURCE = r"""
\tfgames{s}{G0,G1}
\tfgamename{s}{G0}{G_0}
\tfgamename{s}{G1}{G_1}
\begin{tfsource}{s}
\begin{algorithmic}[1]
\tfsegment{Initiator}
\State \(x \gets 0\)
\tfsegment{Responder}
\tfonly{G0}{\State \(y \gets 0\)}
\tfonly{G1}{\State \(y \gets 1\)}
\end{algorithmic}
\end{tfsource}
"""


@needs_pdflatex
def test_crop_stub_does_not_orphan_preceding_line_number(tmp_path):
    r"""Regression: a stub is a \Statex, and algpseudocodex does not run its
    line-closing hook (\algpx@endCodeCommand) on \Statex the way it does on
    \State. So a stub emitted directly after a kept \State line would push
    that \State's content onto the line *below* its own line number, leaving
    the number orphaned. The base \tfsegmentstub runs the hook first; this
    test asserts the numbered line's content (marked with a \Comment) stays
    on the same physical line as its number."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + r"\tfcropdefault{on}"
        + r"""
\tfgames{s}{G0,G1}
\tfgamename{s}{G0}{G_0}
\tfgamename{s}{G1}{G_1}
\begin{tfsource}{s}
\begin{algorithmic}[1]
\tfsegment{First}
\tfonly{G0}{\State \(a \gets 0\)}
\tfonly{G1}{\State \(a \gets 1\)}
\State \(z \gets 9\) \Comment{STAYPUT}
\tfsegment{Middle}
\State \(m \gets 0\)
\tfsegment{Last}
\State \(w \gets 0\)
\end{algorithmic}
\end{tfsource}
\begin{document}
\tfrendergame[diff=G0]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    # "Middle" is unchanged -> stubbed, directly after the STAYPUT \State line.
    layout = _pdftotext_layout(tmp_path)
    assert "unchanged" in layout  # the Middle stub was emitted
    # The STAYPUT line must begin with its line number ("N:  ... STAYPUT"),
    # not be orphaned onto a line of its own below a bare number.
    stayput_lines = [ln for ln in layout.splitlines() if "STAYPUT" in ln]
    assert stayput_lines, "STAYPUT comment did not reach the typeset output"
    assert re.match(r"\s*\d+:\s", stayput_lines[0]), (
        "line number was orphaned from its content: "
        f"{stayput_lines[0]!r}"
    )


@needs_pdflatex
def test_crop_stubs_unchanged_segment(tmp_path):
    r"""A crop=on diff render stubs the unchanged interior "Initiator"
    segment (with its caption) and keeps+highlights the changed final
    "Responder" segment."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + r"\tfcropdefault{on}"
        + _CROP_SOURCE
        + r"""
\begin{document}
\tfrendergame[diff=G0]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    text = _pdftotext(tmp_path)
    assert "unchanged" in text
    assert "Initiator" in text  # stub caption must reach the typeset output
    assert "y" in text  # the changed Responder line's content is kept


@needs_pdflatex
def test_crop_keeps_absolute_line_numbers(tmp_path):
    r"""A cropped render keeps kept lines' ABSOLUTE line numbers from the full
    listing: numbers jump across a stub instead of renumbering contiguously.
    Here p=1, Alpha=(2,3), Beta=(4,5) are stubbed, and the changed Gamma line
    is line 6 in the full listing -- it must render as "6:", not "2:"."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + r"\tfcropdefault{on}"
        + r"""
\tfgames{s}{G0,G1}
\tfgamename{s}{G0}{G_0}
\tfgamename{s}{G1}{G_1}
\begin{tfsource}{s}
\begin{algorithmic}[1]
\State \(p \gets 0\)
\tfsegment{Alpha}
\State \(a1 \gets 0\)
\State \(a2 \gets 0\)
\tfsegment{Beta}
\State \(b1 \gets 0\)
\State \(b2 \gets 0\)
\tfsegment{Gamma}
\tfonly{G0}{\State \(z \gets 0\) \Comment{TAILMARK}}
\tfonly{G1}{\State \(z \gets 1\) \Comment{TAILMARK}}
\end{algorithmic}
\end{tfsource}
\begin{document}
\tfrendergame[diff=G0]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    layout = _pdftotext_layout(tmp_path)
    tail = [ln for ln in layout.splitlines() if "TAILMARK" in ln]
    assert tail, "TAILMARK line missing from output"
    # Absolute number 6 (its position in the full listing), not 2 (its
    # position among the kept lines).
    assert re.match(r"\s*6:\s", tail[0]), tail[0]


@needs_pdflatex
def test_crop_off_renders_full(tmp_path):
    r"""crop=off on the same fixture must fully render both segments -- no
    stub, and the interior "Initiator" content is present too."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + r"\tfcropdefault{on}"
        + _CROP_SOURCE
        + r"""
\begin{document}
\tfrendergame[diff=G0, crop=off]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    text = _pdftotext(tmp_path)
    assert "unchanged" not in text
    assert "x" in text  # interior "Initiator" line, always rendered
    assert "y" in text  # final "Responder" line, always rendered


@needs_pdflatex
def test_crop_requires_diff_full(tmp_path):
    r"""A no-diff clean render must never crop, even with
    \tfcropdefault{on} set."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + r"\tfcropdefault{on}"
        + _CROP_SOURCE
        + r"""
\begin{document}
\tfrendergame{s}{G0}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    text = _pdftotext(tmp_path)
    assert "unchanged" not in text
    assert "x" in text
    assert "y" in text


# ---------------------------------------------------------------------------
# Task 6b: harder crop-render correctness invariants
# ---------------------------------------------------------------------------


@needs_pdflatex
def test_crop_position_alignment_after_skip(tmp_path):
    r"""Skipping the unchanged interior "Early" segment must jump
    \g__tf_pos_int to its recorded end position (\g__tf_seg_endpos_prop) so
    the highlight decision for later \tfonly lines in the kept "Late"
    segment stays aligned with the record pass. Highlight color itself is
    invisible to pdftotext, so \tfchanged is redefined to emit a plain-text
    "HILITE" marker immediately before its content -- if the position jump
    is wrong, the unchanged "q <- 2" line in "Late" would also get
    mis-highlighted, producing 2 HILITE markers instead of 1."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + r"\renewcommand{\tfchanged}[1]{HILITE #1}"
        + r"\tfcropdefault{on}"
        + r"""
\tfgames{s}{G0,G1}
\tfgamename{s}{G0}{G_0}
\tfgamename{s}{G1}{G_1}
\begin{tfsource}{s}
\begin{algorithmic}[1]
\State untagged
\tfsegment{Early}
\tfonly{G0,G1}{\State \(p \gets 1\)}
\tfsegment{Late}
\tfonly{G0,G1}{\State \(q \gets 2\)}
\tfonly{G0}{\State \(r \gets 0\)}
\tfonly{G1}{\State \(r \gets 9\)}
\end{algorithmic}
\end{tfsource}
\begin{document}
\tfrendergame[diff=G0]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    text = _pdftotext(tmp_path)
    # "Early" is stubbed (unchanged across G0/G1, despite containing a
    # \tfonly line that advances the position counter).
    assert "unchanged" in text
    assert "Early" in text
    # Exactly one HILITE: the genuinely changed "r <- 9" line. If the
    # endpos jump were wrong, the unchanged "q <- 2" line in the kept
    # "Late" segment would be mis-highlighted too.
    assert text.count("HILITE") == 1
    assert "9" in text
    assert "q" in text
    assert "2" in text


@needs_pdflatex
def test_crop_stubs_consecutive_inactive_interiors_separately(tmp_path):
    r"""Two consecutive unchanged interior segments ("Alpha", "Beta") each
    emit their OWN stub line (one per skipped segment, on separate lines),
    rather than collapsing into a single comma-joined stub."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + r"\tfcropdefault{on}"
        + r"""
\tfgames{s}{G0,G1}
\tfgamename{s}{G0}{G_0}
\tfgamename{s}{G1}{G_1}
\begin{tfsource}{s}
\begin{algorithmic}[1]
\State untagged
\tfsegment{Alpha}
\tfonly{G0,G1}{\State \(a \gets 1\)}
\tfsegment{Beta}
\tfonly{G0,G1}{\State \(b \gets 2\)}
\tfsegment{Gamma}
\tfonly{G0}{\State \(c \gets 0\)}
\tfonly{G1}{\State \(c \gets 9\)}
\end{algorithmic}
\end{tfsource}
\begin{document}
\tfrendergame[diff=G0]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    text = _pdftotext(tmp_path)
    # One stub per skipped segment, on separate lines -- not a single
    # coalesced "Alpha, Beta" stub.
    assert "Alpha, Beta" not in text
    assert "Alpha" in text
    assert "Beta" in text
    assert text.count("unchanged") == 2
    assert "9" in text  # the changed final "Gamma" content is kept


@needs_pdflatex
def test_crop_all_interior_changed_no_stub(tmp_path):
    r"""When every interior segment differs between G0 and G1, nothing is
    skipped -- no stub is emitted and all content is present."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + r"\tfcropdefault{on}"
        + r"""
\tfgames{s}{G0,G1}
\tfgamename{s}{G0}{G_0}
\tfgamename{s}{G1}{G_1}
\begin{tfsource}{s}
\begin{algorithmic}[1]
\State untagged
\tfsegment{Alpha}
\tfonly{G0}{\State \(a \gets 0\)}
\tfonly{G1}{\State \(a \gets 1\)}
\tfsegment{Beta}
\tfonly{G0}{\State \(b \gets 0\)}
\tfonly{G1}{\State \(b \gets 3\)}
\end{algorithmic}
\end{tfsource}
\begin{document}
\tfrendergame[diff=G0]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    text = _pdftotext(tmp_path)
    assert "unchanged" not in text
    assert "1" in text
    assert "3" in text


# ---------------------------------------------------------------------------
# I1: crop compile path for a non-algpseudocodex, non-cryptocode profile
# ---------------------------------------------------------------------------
#
# I1 documents that PDF crop is unsupported for cryptocode because its
# content lines live inside a \procedure{...}{...} brace group: a
# \tfsegment marker between lines therefore sits *inside* a literal brace
# group, and \regex_split (which operates on the flat stored token list)
# produces two brace-unbalanced fragments -- "Missing brace inserted", no
# PDF. nicodemus's \begin{nicodemus}...\end{nicodemus} (a plain
# \newenvironment built on enumitem's \begin{enumerate}[...]) introduces no
# extra literal brace group around its \item lines, so markers placed
# directly between \item lines (i.e. NOT nested inside an additional
# \nicodemusboxNew{width}{...} wrapper, which -- like \procedure -- would
# reintroduce the same brace-nesting problem) sit at the top brace level of
# the stored tfsource body, exactly like algpseudocodex's \State lines. This
# test is the first green crop path for a profile other than algpseudocodex.

_NICODEMUS_CROP_SOURCE = r"""
\tfgames{s}{G0,G1}
\tfgamename{s}{G0}{G_0}
\tfgamename{s}{G1}{G_1}
\begin{tfsource}{s}
\begin{nicodemus}
\tfsegment{Initiator}
\item $x \gets 0$
\tfsegment{Responder}
\tfonly{G0}{\item $y \gets 0$}
\tfonly{G1}{\item $y \gets 1$}
\end{nicodemus}
\end{tfsource}
"""


@needs_pdflatex
def test_crop_stubs_unchanged_segment_nicodemus(tmp_path):
    r"""crop=on for nicodemus stubs the unchanged interior "Initiator"
    segment and keeps+highlights the changed final "Responder" segment --
    the non-algpseudocodex crop path referenced by I1 actually works when
    \tfsegment markers sit at the top brace level of the tfsource body
    (i.e. directly inside \begin{nicodemus}...\end{nicodemus}, not nested
    inside an additional \nicodemusboxNew{...}{...} group)."""
    tex = (
        _NICODEMUS_PREAMBLE
        + r"\tfcropdefault{on}"
        + _NICODEMUS_CROP_SOURCE
        + r"""
\begin{document}
\tfrendergame[diff=G0]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(
        tmp_path, tex,
        extra_files={"nicodemus.sty": _NICODEMUS_STY_PATH.read_text(encoding="utf-8")},
    )
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    assert "Undefined control sequence" not in result.stdout
    text = _pdftotext(tmp_path)
    assert "unchanged" in text
    assert "Initiator" in text  # stub caption reaches the typeset output
    assert "1" in text  # the changed Responder line's content is kept


@needs_pdflatex
def test_full_render_of_segmented_source_unchanged(tmp_path):
    r"""Regression: a segmented source rendered WITHOUT crop (no
    \tfcropdefault set) must show every segment's content and no stub --
    \tfsegment stays invisible and the token-split path is not entered when
    crop is off."""
    tex = (
        _ALGPSEUDOCODEX_PREAMBLE
        + _CROP_SOURCE
        + r"""
\begin{document}
\tfrendergame[diff=G0]{s}{G1}
\end{document}
"""
    )
    result = _compile_tex(tmp_path, tex)
    assert result.returncode == 0
    _assert_compiled(tmp_path, result)
    text = _pdftotext(tmp_path)
    assert "unchanged" not in text
    assert "x" in text  # interior "Initiator" content, always rendered
    assert "y" in text  # final "Responder" content, always rendered
