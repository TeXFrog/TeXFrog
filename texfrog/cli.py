"""TeXFrog command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .tex_parser import parse_tex_proofs
from .validate import validate_proof


def _show_warnings(proof, base_dir) -> list[str]:
    """Run all validation checks and emit warnings to stderr.

    Returns the list of warning strings.
    """
    warnings = validate_proof(proof, base_dir)
    for msg in warnings:
        click.echo(f"Warning: {msg}", err=True)
    return warnings


def _resolve_input_path(input_path: str) -> Path:
    """Resolve *input_path* to a .tex file.

    If *input_path* is a directory, look for ``proof.tex`` inside it.
    """
    p = Path(input_path).resolve()
    if p.is_dir():
        candidate = p / "proof.tex"
        if candidate.exists():
            return candidate
        raise click.BadParameter(
            f"Directory '{p}' does not contain a proof.tex file.",
            param_hint="'INPUT'",
        )
    return p


@click.group()
def main() -> None:
    """TeXFrog: organise and render cryptographic game-hopping proofs in LaTeX."""


# ---------------------------------------------------------------------------
# texfrog init
# ---------------------------------------------------------------------------

@main.command("init")
@click.argument("directory", default=".", type=click.Path())
@click.option(
    "--package",
    type=click.Choice(["cryptocode", "nicodemus"], case_sensitive=False),
    default="cryptocode",
    show_default=True,
    help="Package profile for the generated templates.",
)
def init_cmd(directory: str, package: str) -> None:
    """Scaffold a new proof with starter files.

    Creates proof.tex with TeXFrog commands, a macros file, and commentary
    stubs in DIRECTORY (default: current directory).
    """
    from .templates import get_templates

    target = Path(directory).resolve()
    target.mkdir(parents=True, exist_ok=True)

    templates = get_templates(package)
    written: list[str] = []
    for filename, (content, description) in templates.items():
        dest = target / filename
        if dest.exists():
            click.echo(f"Skipping {filename} (already exists).", err=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written.append(filename)

    if not written:
        click.echo("No files written (all already exist).")
    else:
        click.echo(
            f"Created {len(written)} file(s) in {target}/:\n  "
            + "\n  ".join(written)
        )
        click.echo(
            f"\nNext steps:\n"
            f"  1. Edit proof.tex and commentary/*.tex to describe your proof.\n"
            f"  2. Compile: pdflatex proof.tex  (in {target}/)\n"
            f"  3. HTML viewer: texfrog html serve {target}/proof.tex"
        )


# ---------------------------------------------------------------------------
# texfrog check
# ---------------------------------------------------------------------------

@main.command("check")
@click.argument("input_file", metavar="INPUT", type=click.Path(exists=True))
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit with code 1 if there are any warnings.",
)
def check_cmd(input_file: str, strict: bool) -> None:
    """Validate a proof without generating any output.

    INPUT is a .tex file with TeXFrog commands, or a directory containing
    proof.tex.  Checks structure, file existence, tag consistency, and game
    references.
    """
    file_path = _resolve_input_path(input_file)

    click.echo(f"Parsing {file_path} …")
    try:
        proofs = parse_tex_proofs(file_path)
    except (ValueError, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Unexpected error parsing input: {type(exc).__name__}: {exc}", err=True)
        sys.exit(1)

    all_warnings: list[str] = []
    for proof in proofs:
        prefix = f"[{proof.source_name}] " if len(proofs) > 1 else ""
        warnings = _show_warnings(proof, file_path.parent)
        all_warnings.extend(warnings)

        n_games = sum(1 for g in proof.games if not g.reduction)
        n_reductions = sum(1 for g in proof.games if g.reduction)
        n_figs = len(proof.figures)

        if not warnings:
            parts = []
            parts.append(f"{n_games} game{'s' if n_games != 1 else ''}")
            parts.append(f"{n_reductions} reduction{'s' if n_reductions != 1 else ''}")
            parts.append(f"{n_figs} figure{'s' if n_figs != 1 else ''}")
            click.echo(f"{prefix}Proof is valid ({', '.join(parts)}).")

    if all_warnings:
        click.echo(f"Total: {len(all_warnings)} warning(s) across {len(proofs)} proof(s).")
        if strict:
            sys.exit(1)


# ---------------------------------------------------------------------------
# texfrog html
# ---------------------------------------------------------------------------

@main.group("html")
def html_group() -> None:
    """Build or serve the interactive HTML proof viewer."""


@html_group.command("build")
@click.argument("input_file", metavar="INPUT", type=click.Path(exists=True))
@click.option(
    "-o", "--output-dir",
    metavar="DIR",
    default=None,
    help="Output directory (default: texfrog_html/ next to INPUT).",
)
@click.option(
    "--keep-tmp",
    is_flag=True,
    default=False,
    help="Keep intermediate LaTeX/PDF files in a temp directory.",
)
def html_build_cmd(input_file: str, output_dir: str | None, keep_tmp: bool) -> None:
    """Build the interactive HTML proof viewer.

    INPUT is a .tex file with TeXFrog commands, or a directory containing
    proof.tex.  Requires pdflatex and pdf2svg (or pdftocairo).
    """
    from .deps import MissingDependencyError, check_html_deps
    from .output.html import build_all_proofs

    try:
        check_html_deps()
    except MissingDependencyError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    file_path = _resolve_input_path(input_file)
    if output_dir is None:
        out = file_path.parent / "texfrog_html"
    else:
        out = Path(output_dir).resolve()

    click.echo(f"Parsing {file_path} …")
    try:
        proofs = parse_tex_proofs(file_path)
    except (ValueError, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Unexpected error parsing input: {type(exc).__name__}: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Building HTML site in {out} …")
    try:
        build_all_proofs(
            proofs, file_path.parent, out, keep_tmp=keep_tmp,
            on_proof_start=lambda name: click.echo(f"  Building proof '{name}' …"),
        )
    except Exception as exc:
        click.echo(f"Error building HTML: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Done. Open {out / 'index.html'} in a browser.")


@html_group.command("serve")
@click.argument("input_file", metavar="INPUT", type=click.Path(exists=True))
@click.option(
    "-o", "--output-dir",
    metavar="DIR",
    default=None,
    help="Output directory (default: texfrog_html/ next to INPUT).",
)
@click.option("--port", default=8080, show_default=True, type=click.IntRange(1024, 65535), help="Port to listen on.")
@click.option("--no-browser", is_flag=True, default=False, help="Don't open a browser.")
@click.option(
    "--keep-tmp",
    is_flag=True,
    default=False,
    help="Keep intermediate LaTeX/PDF files in a temp directory.",
)
@click.option(
    "--no-live-reload",
    is_flag=True,
    default=False,
    help="Disable watching source files and automatic rebuild/reload on changes.",
)
def html_serve_cmd(
    input_file: str,
    output_dir: str | None,
    port: int,
    no_browser: bool,
    keep_tmp: bool,
    no_live_reload: bool,
) -> None:
    """Build and serve the interactive HTML proof viewer on localhost.

    INPUT is a .tex file with TeXFrog commands, or a directory containing
    proof.tex.
    """
    from .deps import MissingDependencyError, check_html_deps
    from .output.html import build_all_proofs

    try:
        check_html_deps()
    except MissingDependencyError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    file_path = _resolve_input_path(input_file)
    if output_dir is None:
        out = file_path.parent / "texfrog_html"
    else:
        out = Path(output_dir).resolve()

    click.echo(f"Parsing {file_path} …")
    try:
        proofs = parse_tex_proofs(file_path)
    except (ValueError, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Unexpected error parsing input: {type(exc).__name__}: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Building HTML site in {out} …")
    try:
        build_all_proofs(
            proofs, file_path.parent, out, keep_tmp=keep_tmp,
            on_proof_start=lambda name: click.echo(f"  Building proof '{name}' …"),
        )
    except Exception as exc:
        click.echo(f"Error building HTML: {exc}", err=True)
        sys.exit(1)

    if not no_live_reload:
        import logging

        from .output.html import serve_html_live
        from .watcher import start_watcher

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )

        version = [1]
        observer = start_watcher(
            file_path, out, keep_tmp=keep_tmp,
            version=version, debounce_seconds=0.5,
        )
        try:
            serve_html_live(out, version, port=port, open_browser=not no_browser)
        finally:
            observer.stop()
            observer.join()
    else:
        from .output.html import serve_html
        serve_html(out, port=port, open_browser=not no_browser)
