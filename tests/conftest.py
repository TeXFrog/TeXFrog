"""Shared fixtures for TeXFrog tests.

Provides a synthetic HTML viewer site (no pdflatex required) and an HTTP
server for Playwright browser tests.
"""

from __future__ import annotations

import json
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest
from jinja2 import Environment, PackageLoader

# ---------------------------------------------------------------------------
# Playwright availability check
# ---------------------------------------------------------------------------


def _playwright_available() -> bool:
    """Return True if Playwright browsers are installed."""
    try:
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.launch()
            browser.close()
        finally:
            pw.stop()
        return True
    except Exception:
        return False


needs_playwright = pytest.mark.skipif(
    not _playwright_available(),
    reason="Playwright browsers not installed (run: playwright install chromium)",
)

# ---------------------------------------------------------------------------
# Synthetic HTML site fixture
# ---------------------------------------------------------------------------

GAMES_DATA = [
    {
        "label": "G0",
        "latex_name": "G_0",
        "description": "Initial game",
        "has_commentary": False,
        "reduction": False,
        "related_games": [],
    },
    {
        "label": "G1",
        "latex_name": "G_1",
        "description": "Game 1",
        "has_commentary": True,
        "reduction": False,
        "related_games": [],
    },
    {
        "label": "Red1",
        "latex_name": "\\mathcal{B}_1",
        "description": "Reduction 1",
        "has_commentary": False,
        "reduction": True,
        "related_games": ["G0", "G1"],
    },
    {
        "label": "G2",
        "latex_name": "G_2",
        "description": "Game 2",
        "has_commentary": False,
        "reduction": False,
        "related_games": [],
    },
    {
        "label": "G3",
        "latex_name": "G_3",
        "description": "Final game",
        "has_commentary": True,
        "reduction": False,
        "related_games": [],
    },
]


def _make_placeholder_svg(label: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
        f'<rect width="200" height="100" fill="#eee" stroke="#ccc"/>'
        f'<text x="100" y="55" text-anchor="middle" font-size="14">{label}</text>'
        "</svg>"
    )


def _load_template_resource(filename: str) -> str:
    """Read a static file from the templates package."""
    import importlib.resources

    ref = importlib.resources.files("texfrog.output.templates").joinpath(filename)
    return ref.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def html_site_dir(tmp_path_factory):
    """Build a synthetic HTML viewer site with placeholder SVGs."""
    site = tmp_path_factory.mktemp("html_site")
    games_dir = site / "games"
    games_dir.mkdir()

    # Determine which SVG variants each game needs
    for i, g in enumerate(GAMES_DATA):
        label = g["label"]
        # Every game gets its main highlighted SVG
        (games_dir / f"{label}.svg").write_text(
            _make_placeholder_svg(label), encoding="utf-8"
        )
        # Clean variant (used by reductions referencing this game)
        (games_dir / f"{label}-clean.svg").write_text(
            _make_placeholder_svg(f"{label}-clean"), encoding="utf-8"
        )
        # Removed variant (for side-by-side with next game)
        if not g["reduction"]:
            (games_dir / f"{label}-removed.svg").write_text(
                _make_placeholder_svg(f"{label}-removed"), encoding="utf-8"
            )
        # Commentary SVG
        if g["has_commentary"]:
            (games_dir / f"{label}_commentary.svg").write_text(
                _make_placeholder_svg(f"{label} commentary"), encoding="utf-8"
            )

    # Render index.html from Jinja2 template
    jinja_env = Environment(
        loader=PackageLoader("texfrog.output", "templates"),
        autoescape=True,
    )
    template = jinja_env.get_template("index.html.j2")
    html = template.render(
        games_json=json.dumps(GAMES_DATA, ensure_ascii=False, indent=2),
        mathjax_macros="",
    )
    # Neutralize MathJax for testing: the template sets a config object that
    # makes window.MathJax truthy before the CDN loads typesetPromise, which
    # would crash showGame().  Remove the CDN script and config entirely.
    html = html.replace(
        "MathJax = { tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] } };",
        "MathJax = null;",
    )
    html = html.replace(
        '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>',
        "",
    )
    (site / "index.html").write_text(html, encoding="utf-8")

    # Copy static assets
    (site / "style.css").write_text(
        _load_template_resource("style.css"), encoding="utf-8"
    )
    (site / "app.js").write_text(
        _load_template_resource("app.js"), encoding="utf-8"
    )

    return site


# ---------------------------------------------------------------------------
# HTTP server fixture
# ---------------------------------------------------------------------------


class _QuietHandler(SimpleHTTPRequestHandler):
    """HTTP handler that suppresses log output."""

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="session")
def html_server(html_site_dir):
    """Start a local HTTP server serving the synthetic HTML site."""
    handler = partial(_QuietHandler, directory=str(html_site_dir))
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/"
    server.shutdown()
