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

import concurrent.futures
import http.server
import importlib.resources
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from typing import Optional

from jinja2 import Environment, PackageLoader

from ..filter import compute_removed_lines, filter_for_game
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
\newcommand{{\tfremoved}}[1]{{\textcolor{{red}}{{\sbox0{{\strut\ensuremath{{#1}}}}\rlap{{\usebox0}}\rule[0.4ex]{{\wd0}}{{0.5pt}}}}}}
\newcommand{{\tfgamelabel}}[2]{{#2 \pccomment{{#1}}}}
{macro_inputs}
{gamename_defs}
\pagestyle{{empty}}
\begin{{document}}
\input{{{game_file}}}
\end{{document}}
"""

# Commentary wrapper: uses article class (same as game wrapper) with pdfcrop
# to trim whitespace.  \raggedright avoids justified text filling to a fixed
# \textwidth so the cropped result is tight around the prose.
_COMMENTARY_WRAPPER_TEMPLATE = r"""\documentclass{{article}}
\usepackage[letterpaper,margin=1in]{{geometry}}
\usepackage[n,advantage,operators,sets,adversary,landau,probability,notions,logic,ff,mm,primitives,events,complexity,oracles,asymptotics,keys]{{cryptocode}}
\usepackage{{amsfonts,amsmath,amsthm}}
\usepackage{{adjustbox}}
\usepackage[dvipsnames,table]{{xcolor}}
{macro_inputs}
{gamename_defs}
\pagestyle{{empty}}
\begin{{document}}
\raggedright
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
    game_names: dict[str, str] | None = None,
    wrapper_template: str = _WRAPPER_TEMPLATE,
    converter: str | None = None,
) -> None:
    """Compile one game's LaTeX file to an SVG image.

    Args:
        game_label: Used for error messages.
        game_tex_path: Absolute path to the game's ``.tex`` file.
        macro_paths: Macro file paths (relative to proof_dir).
        proof_dir: Directory containing macro files.
        svg_out_path: Where to write the resulting SVG.
        game_names: Optional mapping from game label to ``latex_name``.
            When provided, ``\\tfgamename`` definitions are added to the
            wrapper preamble so that commentary can reference game names.
        wrapper_template: LaTeX wrapper template string. Defaults to
            ``_WRAPPER_TEMPLATE``; use ``_COMMENTARY_WRAPPER_TEMPLATE``
            for prose commentary (uses ``varwidth`` for tight cropping).
        converter: SVG converter tool name ('pdf2svg' or 'pdftocairo').
            If ``None``, auto-detected via ``_find_svg_converter()``.

    Raises:
        RuntimeError: If pdflatex or SVG conversion fails.
        EnvironmentError: If required tools are not found.
    """
    if converter is None:
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

        # Build \tfgamename definitions if game_names were provided.
        if game_names:
            gn_lines = [
                r"\makeatletter",
                r"\providecommand{\tfgamename}[1]{\ensuremath{\@nameuse{tfgn@#1}}}",
            ]
            for label, latex_name in game_names.items():
                gn_lines.append(f"\\@namedef{{tfgn@{label}}}{{{latex_name}}}")
            gn_lines.append(r"\makeatother")
            gamename_defs = "\n".join(gn_lines)
        else:
            gamename_defs = ""

        wrapper_src = wrapper_template.format(
            macro_inputs=macro_inputs,
            gamename_defs=gamename_defs,
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


_jinja_env = Environment(
    loader=PackageLoader("texfrog.output", "templates"),
    autoescape=False,
)


def _load_template_resource(filename: str) -> str:
    """Read a static file from the templates package."""
    ref = importlib.resources.files("texfrog.output.templates").joinpath(filename)
    return ref.read_text(encoding="utf-8")


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

    # Check required tools upfront (once) before spawning worker threads.
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

    # Step 1: generate LaTeX files in a temp directory.
    with tempfile.TemporaryDirectory() as tmp:
        latex_dir = Path(tmp)
        generate_latex(proof, latex_dir)

        # Generate removed-highlight .tex files for the side-by-side view.
        # Each non-reduction game (except the last one) may appear as the
        # "previous" panel, with red strikethrough on lines removed/changed
        # in the next non-reduction game.  Reductions are skipped since they
        # use the related_games display instead.
        non_red_games = [g for g in proof.games if not g.reduction]
        for i, game in enumerate(non_red_games[:-1]):
            prev_lines = filter_for_game(proof.source_lines, game.label)
            next_game = non_red_games[i + 1]
            next_lines = filter_for_game(proof.source_lines, next_game.label)
            removed_indices = compute_removed_lines(prev_lines, next_lines)
            _write_game_file(
                game.label, prev_lines, removed_indices,
                latex_dir / f"{game.label}-removed.tex",
                macro=r"\tfremoved",
            )

        # Generate clean (no-highlight) .tex files for related_games references.
        clean_labels: set[str] = set()
        for game in proof.games:
            if game.related_games:
                clean_labels.update(game.related_games)
        for label in clean_labels:
            clean_lines = filter_for_game(proof.source_lines, label)
            _write_game_file(
                label, clean_lines, set(),
                latex_dir / f"{label}-clean.tex",
            )

        # Step 2: compile all games to SVG in parallel.
        _placeholder_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60">'
            '<text x="10" y="40" font-family="monospace" font-size="14">'
            '[SVG render failed for {label}]</text></svg>'
        )
        game_names = {g.label: g.latex_name for g in proof.games}

        # Collect all compilation tasks as (task_label, tex_path, svg_path,
        # game_names_arg, wrapper_template) tuples.
        tasks: list[tuple[str, Path, Path, dict[str, str] | None, str]] = []
        for i, game in enumerate(proof.games):
            label = game.label
            # Highlighted version
            tasks.append((
                label,
                (latex_dir / f"{label}.tex").resolve(),
                games_dir / f"{label}.svg",
                None,
                _WRAPPER_TEMPLATE,
            ))
            # Removed (red strikethrough) version — needed for non-reduction
            # games that have a successor non-reduction game.
            if not game.reduction and game in non_red_games[:-1]:
                tasks.append((
                    f"{label}-removed",
                    (latex_dir / f"{label}-removed.tex").resolve(),
                    games_dir / f"{label}-removed.svg",
                    None,
                    _WRAPPER_TEMPLATE,
                ))
            # Clean (no-highlight) version — needed for related_games display.
            if label in clean_labels:
                tasks.append((
                    f"{label}-clean",
                    (latex_dir / f"{label}-clean.tex").resolve(),
                    games_dir / f"{label}-clean.svg",
                    None,
                    _WRAPPER_TEMPLATE,
                ))
            # Commentary
            commentary = proof.commentary.get(label, "")
            if commentary.strip():
                tasks.append((
                    f"{label}_commentary",
                    (latex_dir / f"{label}_commentary.tex").resolve(),
                    games_dir / f"{label}_commentary.svg",
                    game_names,
                    _COMMENTARY_WRAPPER_TEMPLATE,
                ))

        def _compile_task(
            task: tuple[str, Path, Path, dict[str, str] | None, str],
        ) -> None:
            task_label, tex_path, svg_path, gn, tmpl = task
            print(f"  Compiling {task_label} …", file=sys.stderr)
            try:
                _compile_game_to_svg(
                    task_label, tex_path, proof.macros, proof_dir,
                    svg_path, game_names=gn, wrapper_template=tmpl,
                    converter=converter,
                )
            except (RuntimeError, EnvironmentError) as exc:
                print(
                    f"    Warning: could not render {task_label}: {exc}",
                    file=sys.stderr,
                )
                svg_path.write_text(
                    _placeholder_svg.format(label=task_label), encoding="utf-8",
                )

        max_workers = min(len(tasks), os.cpu_count() or 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            list(pool.map(_compile_task, tasks))

    # Step 3: assemble the site.
    game_names = {g.label: g.latex_name for g in proof.games}
    games_data = []
    for game in proof.games:
        games_data.append({
            "label": game.label,
            "latex_name": game.latex_name,
            "description": _expand_tfgamename(game.description, game_names),
            "has_commentary": bool(proof.commentary.get(game.label, "").strip()),
            "reduction": game.reduction,
            "related_games": game.related_games,
        })

    template = _jinja_env.get_template("index.html.j2")
    html = template.render(
        games_json=json.dumps(games_data, ensure_ascii=False, indent=2),
        mathjax_macros=_extract_mathjax_macros(proof.macros, proof_dir),
    )

    (output_dir / "index.html").write_text(html, encoding="utf-8")
    (output_dir / "style.css").write_text(
        _load_template_resource("style.css"), encoding="utf-8"
    )
    (output_dir / "app.js").write_text(
        _load_template_resource("app.js"), encoding="utf-8"
    )


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
