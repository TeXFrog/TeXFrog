"""HTML output generator for TeXFrog.

Compiles each game's LaTeX to a PDF via pdflatex, converts to SVG via
pdf2svg (or pdftocairo), and assembles a self-contained interactive HTML
site.

System requirements (not installed via pip):
    pdflatex   — part of a TeX distribution (e.g. TeX Live, MacTeX)
    pdf2svg    — https://github.com/dawbarton/pdf2svg  OR
    pdftocairo — part of poppler-utils (usually available via your package manager)
"""

from __future__ import annotations

import http.server
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from typing import Optional

from jinja2 import Environment, PackageLoader, select_autoescape

from ..filter import filter_for_game
from ..model import Proof
from .latex import _write_game_file, generate_latex

# ---------------------------------------------------------------------------
# LaTeX wrapper template used to compile individual game files to PDF
# ---------------------------------------------------------------------------

_WRAPPER_TEMPLATE = r"""\documentclass{{article}}
% Standard letter paper; pdfcrop removes whitespace after compilation.
% Pseudocode box environments (pcvstack etc.) use their natural width anyway.
\usepackage[letterpaper,margin=1in]{{geometry}}
\usepackage[n,advantage,operators,sets,adversary,landau,probability,notions,logic,ff,mm,primitives,events,complexity,oracles,asymptotics,keys]{{cryptocode}}
\usepackage{{amsfonts,amsmath,amsthm}}
\usepackage{{adjustbox}}
\usepackage[dvipsnames,table]{{xcolor}}
\newcommand{{\solidbox}}[1]{{\adjustbox{{fbox}}{{\strut #1}}}}
\newcommand{{\graybox}}[1]{{\adjustbox{{cframe=black!15, bgcolor=black!15}}{{\strut #1}}}}
\newcommand{{\highlightbox}}[2][RoyalBlue!20]{{\adjustbox{{cframe=#1, bgcolor=#1}}{{\strut #2}}}}
\newcommand{{\tfchanged}}[1]{{\highlightbox{{\ensuremath{{#1}}}}}}
\newcommand{{\tfgamelabel}}[2]{{#2 \pccomment{{#1}}}}
{macro_inputs}
\pagestyle{{empty}}
\begin{{document}}
\input{{{game_file}}}
\end{{document}}
"""


def _find_svg_converter() -> Optional[str]:
    """Return 'pdf2svg' or 'pdftocairo' if either is on PATH, else None."""
    for tool in ("pdf2svg", "pdftocairo"):
        if shutil.which(tool):
            return tool
    return None


def _pdfcrop(pdf_path: Path) -> Path:
    """Run pdfcrop on ``pdf_path`` and return the path to the cropped PDF.

    ``pdfcrop`` strips whitespace margins from a PDF page.  If ``pdfcrop`` is
    not available, the original ``pdf_path`` is returned unchanged.

    Args:
        pdf_path: Input PDF (modified in-place to ``<stem>-crop.pdf``).

    Returns:
        Path to the cropped PDF (or the original if pdfcrop is unavailable).
    """
    if not shutil.which("pdfcrop"):
        return pdf_path
    cropped = pdf_path.with_name(pdf_path.stem + "-crop.pdf")
    result = subprocess.run(
        ["pdfcrop", str(pdf_path), str(cropped)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and cropped.exists():
        return cropped
    return pdf_path


def _pdf_to_svg(pdf_path: Path, svg_path: Path, converter: str) -> None:
    """Convert a single-page PDF to SVG.

    Args:
        pdf_path: Input PDF file.
        svg_path: Output SVG file.
        converter: Either 'pdf2svg' or 'pdftocairo'.

    Raises:
        RuntimeError: If conversion fails.
    """
    if converter == "pdf2svg":
        cmd = ["pdf2svg", str(pdf_path), str(svg_path)]
    else:  # pdftocairo
        # pdftocairo -svg writes to the exact output path specified (no suffix added).
        cmd = ["pdftocairo", "-svg", str(pdf_path), str(svg_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{converter} failed for {pdf_path}:\n{result.stderr}"
        )


def _compile_game_to_svg(
    game_label: str,
    game_tex_path: Path,
    macro_paths: list[str],
    proof_dir: Path,
    svg_out_path: Path,
) -> None:
    """Compile one game's LaTeX file to an SVG image.

    Args:
        game_label: Used for error messages.
        game_tex_path: Absolute path to the game's ``.tex`` file.
        macro_paths: Macro file paths (relative to proof_dir).
        proof_dir: Directory containing macro files.
        svg_out_path: Where to write the resulting SVG.

    Raises:
        RuntimeError: If pdflatex or SVG conversion fails.
        EnvironmentError: If required tools are not found.
    """
    converter = _find_svg_converter()
    if converter is None:
        raise EnvironmentError(
            "Neither pdf2svg nor pdftocairo found on PATH. "
            "Install one of them to generate the HTML site."
        )
    if shutil.which("pdflatex") is None:
        raise EnvironmentError(
            "pdflatex not found on PATH. "
            "Install a TeX distribution (e.g. TeX Live or MacTeX)."
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Copy the game .tex file into the temp dir so pdflatex runs from a
        # path that contains no spaces (LaTeX's \input{} can't handle spaces).
        game_local = tmp_path / "game.tex"
        shutil.copy2(game_tex_path, game_local)

        # Copy each macro file into the temp dir under a flat name.
        # Build the corresponding \input{} lines using those local names.
        macro_input_lines: list[str] = []
        for i, rel_path in enumerate(macro_paths):
            src = (proof_dir / rel_path).resolve()
            local_name = f"macros_{i:02d}_{src.name}"
            shutil.copy2(src, tmp_path / local_name)
            macro_input_lines.append(f"\\input{{{local_name}}}")
        macro_inputs = "\n".join(macro_input_lines)

        wrapper_src = _WRAPPER_TEMPLATE.format(
            macro_inputs=macro_inputs,
            game_file="game.tex",
        )

        wrapper_tex = tmp_path / "wrapper.tex"
        wrapper_tex.write_text(wrapper_src, encoding="utf-8")

        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "wrapper.tex"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        pdf_path = tmp_path / "wrapper.pdf"
        if result.returncode != 0 or not pdf_path.exists():
            raise RuntimeError(
                f"pdflatex failed for game {game_label}:\n{result.stdout[-3000:]}"
            )

        cropped_pdf = _pdfcrop(pdf_path)
        _pdf_to_svg(cropped_pdf, svg_out_path, converter)


# ---------------------------------------------------------------------------
# HTML site assembly
# ---------------------------------------------------------------------------


def _extract_mathjax_macros(macro_paths: list[str], proof_dir: Path) -> str:
    """Extract LaTeX macro definitions from user macro files for MathJax.

    Collects lines that start with ``\\newcommand``, ``\\renewcommand``,
    ``\\providecommand``, ``\\DeclareMathOperator``, or ``\\def`` so that
    MathJax can render the same custom commands used in the LaTeX source.
    """
    MACRO_PREFIXES = (
        "\\newcommand", "\\renewcommand", "\\providecommand",
        "\\DeclareMathOperator", "\\def",
    )
    collected: list[str] = []
    for rel_path in macro_paths:
        src = (proof_dir / rel_path).resolve()
        try:
            text = src.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(p) for p in MACRO_PREFIXES):
                collected.append(stripped)
    return "\n".join(collected)


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TeXFrog Proof Viewer</title>
  <link rel="stylesheet" href="style.css">
  <script>
  MathJax = {{ tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] }} }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
</head>
<body>
  <!-- Hidden block so MathJax learns user-defined macros before rendering -->
  <div id="mathjax-macros" style="display:none">\\[
{mathjax_macros}
  \\]</div>
  <div id="nav">
    <h2>Games</h2>
    <ul id="game-list">
    </ul>
  </div>
  <div id="main">
    <div id="controls">
      <button id="btn-prev" onclick="navigate(-1)">&#8592; Prev</button>
      <span id="game-title"></span>
      <button id="btn-next" onclick="navigate(+1)">Next &#8594;</button>
    </div>
    <div id="game-display">
      <div id="game-svg-container"></div>
      <div id="commentary-box"></div>
    </div>
  </div>
  <script src="app.js"></script>
  <script>
    const GAMES = {games_json};
    init(GAMES);
  </script>
</body>
</html>
"""

_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body { display: flex; height: 100vh; font-family: sans-serif; }
#nav { width: 260px; min-width: 200px; background: #f4f4f4; border-right: 1px solid #ccc;
       overflow-y: auto; padding: 1rem; }
#nav h2 { font-size: 1rem; margin-bottom: 0.75rem; color: #555; text-transform: uppercase;
           letter-spacing: 0.05em; }
#game-list { list-style: none; }
#game-list li { cursor: pointer; padding: 0.5rem 0.75rem; border-radius: 4px;
                margin-bottom: 0.25rem; transition: background 0.15s; }
#game-list li:hover { background: #e0e0e0; }
#game-list li.active { background: #4a90d9; color: #fff; }
#game-list .game-label { font-weight: bold; font-size: 0.9rem; }
#game-list .game-desc { font-size: 0.75rem; color: inherit; opacity: 0.8;
                         margin-top: 0.2rem; }
#main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
#controls { display: flex; align-items: center; padding: 0.75rem 1rem;
            border-bottom: 1px solid #ccc; gap: 1rem; }
#controls button { padding: 0.4rem 1rem; border: 1px solid #aaa; border-radius: 4px;
                   background: #fff; cursor: pointer; font-size: 0.95rem; }
#controls button:hover { background: #e8e8e8; }
#game-title { flex: 1; text-align: center; font-size: 1.1rem; }
#game-display { flex: 1; overflow-y: auto; padding: 1.5rem; display: flex;
                flex-direction: column; gap: 1.5rem; }
#game-svg-container { display: flex; gap: 0.5rem; justify-content: center; }
.game-panel { text-align: center; min-width: 0; }
.game-panel-header { font-size: 1rem; margin-bottom: 0.25rem; color: #333; }
.game-panel img { max-width: 100%; }
#commentary-box { background: #fafafa; border: 1px solid #ddd; border-radius: 6px;
                  padding: 1rem; font-size: 0.9rem; line-height: 1.6; }
#commentary-box:empty { display: none; }
"""

_JS = """\
let currentIndex = 0;
let games = [];

function init(gamesData) {
  games = gamesData;
  const list = document.getElementById('game-list');
  games.forEach((g, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<div class="game-label">$${g.latex_name}$</div>
                    <div class="game-desc">${g.description}</div>`;
    li.onclick = () => showGame(i);
    list.appendChild(li);
  });
  // Navigate to hash or first game
  const hash = window.location.hash.slice(1);
  const idx = hash ? games.findIndex(g => g.label === hash) : -1;
  showGame(idx >= 0 ? idx : 0);
}

function makePanel(label, latexName, svgSrc) {
  const panel = document.createElement('div');
  panel.className = 'game-panel';
  const header = document.createElement('div');
  header.className = 'game-panel-header';
  header.innerHTML = `$${latexName}$`;
  panel.appendChild(header);
  const img = new Image();
  img.alt = label;
  img.src = svgSrc;
  panel.appendChild(img);
  return panel;
}

function showGame(idx) {
  if (idx < 0 || idx >= games.length) return;
  currentIndex = idx;

  const g = games[idx];
  window.location.hash = g.label;

  // Update nav highlight
  document.querySelectorAll('#game-list li').forEach((li, i) => {
    li.classList.toggle('active', i === idx);
    if (i === idx) li.scrollIntoView({ block: 'nearest' });
  });

  // Update title
  document.getElementById('game-title').innerHTML = `$${g.latex_name}$`;

  // Build side-by-side display
  const container = document.getElementById('game-svg-container');
  container.innerHTML = '';

  if (idx > 0 && !g.reduction) {
    // Show previous game (clean, no highlights) on the left
    const prev = games[idx - 1];
    container.appendChild(
      makePanel(prev.label, prev.latex_name, `games/${prev.label}-clean.svg`)
    );
  }

  // Current game (with highlights) on the right, or alone for first game / reductions
  container.appendChild(
    makePanel(g.label, g.latex_name, `games/${g.label}.svg`)
  );

  // Update commentary
  const box = document.getElementById('commentary-box');
  box.innerHTML = g.commentary || '';

  // Re-typeset MathJax
  if (window.MathJax) {
    MathJax.typesetPromise([
      document.getElementById('game-title'),
      document.getElementById('game-svg-container'),
      document.getElementById('commentary-box'),
      document.getElementById('nav'),
    ]).catch(console.error);
  }

  // Update buttons
  document.getElementById('btn-prev').disabled = (idx === 0);
  document.getElementById('btn-next').disabled = (idx === games.length - 1);
}

function navigate(delta) {
  showGame(currentIndex + delta);
}

document.addEventListener('keydown', e => {
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') navigate(-1);
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') navigate(+1);
});
"""


def _expand_tfgamename(text: str, game_names: dict[str, str]) -> str:
    r"""Replace ``\tfgamename{LABEL}`` with the game's ``latex_name``.

    MathJax does not support ``\csname``/``\@nameuse``, so we pre-expand
    game-name references before the text reaches the HTML viewer.
    When a ``\tfgamename`` appears outside math mode the replacement is
    wrapped in ``$…$``; inside an existing math context (``$…$``,
    ``\(…\)``, or ``\[…\]``) the bare ``latex_name`` is emitted to
    avoid creating invalid nested delimiters.

    LaTeX comments (``%`` to end-of-line) are passed through without
    affecting math-mode tracking.

    Args:
        text: Raw LaTeX/commentary string.
        game_names: Mapping from game label to ``latex_name``.

    Returns:
        The text with all recognised ``\tfgamename{…}`` occurrences replaced.
    """
    _TOKEN = re.compile(
        r"(?<!\\)%[^\n]*"              # LaTeX comment: % to end-of-line
        r"|(?<!\\)\$"                   # unescaped $
        r"|\\[(\[]"                     # \( or \[
        r"|\\[)\]]"                     # \) or \]
        r"|\\tfgamename\{([^}]+)\}"
    )
    parts: list[str] = []
    last_end = 0
    in_math = False
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        parts.append(text[last_end:m.start()])
        if tok.startswith("%"):
            parts.append(tok)           # pass comment through unchanged
        elif tok == "$":
            in_math = not in_math
            parts.append(tok)
        elif tok in (r"\(", r"\["):
            in_math = True
            parts.append(tok)
        elif tok in (r"\)", r"\]"):
            in_math = False
            parts.append(tok)
        else:
            # \tfgamename match
            label = m.group(1)
            name = game_names.get(label)
            if name is None:
                parts.append(tok)       # leave unrecognised labels unchanged
            else:
                parts.append(name if in_math else f"${name}$")
        last_end = m.end()
    parts.append(text[last_end:])
    return "".join(parts)


def generate_html(proof: Proof, proof_dir: Path, output_dir: Path) -> None:
    """Build the interactive HTML proof viewer.

    Steps:
    1. Generate LaTeX output (per-game ``.tex`` files) in a temp dir.
    2. Compile each game's ``.tex`` to SVG via pdflatex + pdf2svg/pdftocairo.
    3. Write ``index.html``, ``style.css``, ``app.js``, and game SVGs.

    Args:
        proof: The parsed proof.
        proof_dir: Directory containing the proof's macro files.
        output_dir: Destination directory for the HTML site.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    games_dir = output_dir / "games"
    games_dir.mkdir(exist_ok=True)

    # Step 1: generate LaTeX files in a temp directory.
    with tempfile.TemporaryDirectory() as tmp:
        latex_dir = Path(tmp)
        generate_latex(proof, latex_dir)

        # Also generate clean (no-highlight) .tex files for the side-by-side
        # view.  Each game except the last may appear as the "previous" panel.
        for game in proof.games[:-1]:
            clean_lines = filter_for_game(proof.source_lines, game.label)
            _write_game_file(
                game.label, clean_lines, set(),
                latex_dir / f"{game.label}-clean.tex",
            )

        # Step 2: compile each game to SVG (highlighted + clean).
        _placeholder_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60">'
            '<text x="10" y="40" font-family="monospace" font-size="14">'
            '[SVG render failed for {label}]</text></svg>'
        )
        for i, game in enumerate(proof.games):
            label = game.label
            # Highlighted version
            print(f"  Compiling {label} …", file=sys.stderr)
            game_tex = latex_dir / f"{label}.tex"
            svg_path = games_dir / f"{label}.svg"
            try:
                _compile_game_to_svg(
                    label,
                    game_tex.resolve(),
                    proof.macros,
                    proof_dir,
                    svg_path,
                )
            except (RuntimeError, EnvironmentError) as exc:
                print(f"    Warning: could not render {label}: {exc}", file=sys.stderr)
                svg_path.write_text(
                    _placeholder_svg.format(label=label), encoding="utf-8",
                )

            # Clean (no-highlight) version — needed for all but the last game.
            if i < len(proof.games) - 1:
                print(f"  Compiling {label} (clean) …", file=sys.stderr)
                clean_tex = latex_dir / f"{label}-clean.tex"
                clean_svg = games_dir / f"{label}-clean.svg"
                try:
                    _compile_game_to_svg(
                        f"{label}-clean",
                        clean_tex.resolve(),
                        proof.macros,
                        proof_dir,
                        clean_svg,
                    )
                except (RuntimeError, EnvironmentError) as exc:
                    print(f"    Warning: could not render {label} (clean): {exc}",
                          file=sys.stderr)
                    clean_svg.write_text(
                        _placeholder_svg.format(label=f"{label}-clean"),
                        encoding="utf-8",
                    )

    # Step 3: assemble the site.
    game_names = {g.label: g.latex_name for g in proof.games}
    games_data = []
    for game in proof.games:
        games_data.append({
            "label": game.label,
            "latex_name": game.latex_name,
            "description": _expand_tfgamename(game.description, game_names),
            "commentary": _expand_tfgamename(
                proof.commentary.get(game.label, ""), game_names
            ),
            "reduction": game.reduction,
        })

    nav_items = "\n".join(
        f'      <li onclick="showGame({i})">'
        f'<div class="game-label">${g["latex_name"]}$</div>'
        f'<div class="game-desc">{g["description"]}</div></li>'
        for i, g in enumerate(games_data)
    )

    html = _HTML_TEMPLATE.format(
        nav_items=nav_items,
        games_json=json.dumps(games_data, ensure_ascii=False, indent=2),
        mathjax_macros=_extract_mathjax_macros(proof.macros, proof_dir),
    )

    (output_dir / "index.html").write_text(html, encoding="utf-8")
    (output_dir / "style.css").write_text(_CSS, encoding="utf-8")
    (output_dir / "app.js").write_text(_JS, encoding="utf-8")


def serve_html(html_dir: Path, port: int = 8080, open_browser: bool = True) -> None:
    """Serve the HTML site on localhost and optionally open a browser.

    Args:
        html_dir: Directory containing the built HTML site.
        port: TCP port to listen on.
        open_browser: Whether to launch the default browser.
    """
    import os

    os.chdir(html_dir)

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # silence per-request logging

    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Serving proof viewer at {url}  (Ctrl-C to stop)")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
