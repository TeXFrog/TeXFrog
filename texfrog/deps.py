"""Check for required external tools before HTML builds."""

from __future__ import annotations

import platform
import shutil


class MissingDependencyError(Exception):
    """Raised when a required external tool is not found on PATH."""


def _platform_hint(tool: str) -> str:
    """Return a platform-aware install suggestion for *tool*."""
    system = platform.system()
    hints = {
        "pdflatex": {
            "Darwin": "brew install --cask mactex",
            "Linux": "apt install texlive-full",
        },
        "pdftocairo": {
            "Darwin": "brew install poppler",
            "Linux": "apt install poppler-utils",
        },
        "pdf2svg": {
            "Darwin": "brew install pdf2svg",
            "Linux": "apt install pdf2svg",
        },
        "pdfcrop": {
            "Darwin": "brew install --cask mactex",
            "Linux": "apt install texlive-extra-utils",
        },
    }
    tool_hints = hints.get(tool, {})
    hint = tool_hints.get(system)
    if hint:
        return f"  Install: {hint}"
    return ""


def check_html_deps() -> str:
    """Verify that required tools for HTML builds are available.

    Checks for ``pdflatex`` and an SVG converter (``pdftocairo`` or
    ``pdf2svg``).  Warns (but does not fail) if ``pdfcrop`` is missing.

    Returns:
        The name of the available SVG converter (``"pdftocairo"`` or
        ``"pdf2svg"``).

    Raises:
        MissingDependencyError: If ``pdflatex`` or both SVG converters
            are missing.
    """
    errors: list[str] = []

    if not shutil.which("pdflatex"):
        msg = "pdflatex not found. Install a TeX distribution (e.g. TeX Live or MacTeX)."
        hint = _platform_hint("pdflatex")
        if hint:
            msg += "\n" + hint
        errors.append(msg)

    converter = None
    for tool in ("pdftocairo", "pdf2svg"):
        if shutil.which(tool):
            converter = tool
            break

    if converter is None:
        msg = (
            "Neither pdftocairo nor pdf2svg found. "
            "Install Poppler (includes pdftocairo) or pdf2svg."
        )
        hint_cairo = _platform_hint("pdftocairo")
        hint_svg = _platform_hint("pdf2svg")
        if hint_cairo or hint_svg:
            msg += "\n" + (hint_cairo or hint_svg)
        errors.append(msg)

    if errors:
        raise MissingDependencyError("\n\n".join(errors))

    if not shutil.which("pdfcrop"):
        import sys
        hint = _platform_hint("pdfcrop")
        msg = "pdfcrop not found; PDFs will not be cropped (wider margins in SVGs)."
        if hint:
            msg += "\n" + hint
        print(f"Warning: {msg}", file=sys.stderr)

    return converter
