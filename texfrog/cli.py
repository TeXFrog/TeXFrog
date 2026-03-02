"""TeXFrog command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .parser import parse_proof, validate_tags
from .output.latex import generate_latex
from .templates import get_templates
from .validate import validate_proof


def _show_tag_warnings(proof) -> None:
    """Emit tag validation warnings to stderr."""
    for msg in validate_tags(proof):
        click.echo(f"Warning: {msg}", err=True)


def _show_warnings(proof, base_dir) -> list[str]:
    """Run all validation checks and emit warnings to stderr.

    Returns the list of warning strings.
    """
    warnings = validate_proof(proof, base_dir)
    for msg in warnings:
        click.echo(f"Warning: {msg}", err=True)
    return warnings


def _resolve_yaml_path(input_path: str) -> Path:
    """Resolve *input_path* to a YAML file.

    If *input_path* is a directory, look for ``proof.yaml`` inside it.
    """
    p = Path(input_path).resolve()
    if p.is_dir():
        candidate = p / "proof.yaml"
        if not candidate.exists():
            raise click.BadParameter(
                f"Directory '{p}' does not contain a proof.yaml file.",
                param_hint="'INPUT'",
            )
        return candidate
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

    Creates proof.yaml, a combined source file, and a macros file in DIRECTORY
    (default: current directory).  The generated proof is immediately buildable
    with ``texfrog latex``.
    """
    target = Path(directory).resolve()
    target.mkdir(parents=True, exist_ok=True)

    templates = get_templates(package)
    written: list[str] = []
    for filename, (content, description) in templates.items():
        dest = target / filename
        if dest.exists():
            click.echo(f"Skipping {filename} (already exists).", err=True)
            continue
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
            f"  1. Edit proof.yaml and games_source.tex to describe your proof.\n"
            f"  2. Run: texfrog latex {directory}/proof.yaml\n"
            f"  3. Run: texfrog html serve {directory}/proof.yaml"
        )


# ---------------------------------------------------------------------------
# texfrog check
# ---------------------------------------------------------------------------

@main.command("check")
@click.argument("input_yaml", metavar="INPUT", type=click.Path(exists=True))
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit with code 1 if there are any warnings.",
)
def check_cmd(input_yaml: str, strict: bool) -> None:
    """Validate a proof without generating any output.

    INPUT is a proof YAML file or a directory containing proof.yaml.
    Checks YAML structure, file existence, tag consistency, and game
    references.  Prints a summary and exits with code 0 if valid (or if
    only warnings are found and --strict is not set), or code 1 on errors.
    """
    yaml_path = _resolve_yaml_path(input_yaml)

    click.echo(f"Parsing {yaml_path} …")
    try:
        proof = parse_proof(yaml_path)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    warnings = _show_warnings(proof, yaml_path.parent)

    n_games = sum(1 for g in proof.games if not g.reduction)
    n_reductions = sum(1 for g in proof.games if g.reduction)
    n_figs = len(proof.figures)

    if warnings:
        click.echo(f"Proof has {len(warnings)} warning(s).")
        if strict:
            sys.exit(1)
    else:
        parts = []
        parts.append(f"{n_games} game{'s' if n_games != 1 else ''}")
        parts.append(f"{n_reductions} reduction{'s' if n_reductions != 1 else ''}")
        parts.append(f"{n_figs} figure{'s' if n_figs != 1 else ''}")
        click.echo(f"Proof is valid ({', '.join(parts)}).")


# ---------------------------------------------------------------------------
# texfrog latex
# ---------------------------------------------------------------------------

@main.command("latex")
@click.argument("input_yaml", metavar="INPUT.yaml", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-o", "--output-dir",
    metavar="DIR",
    default=None,
    help="Output directory (default: texfrog_latex/ next to INPUT.yaml).",
)
def latex_cmd(input_yaml: str, output_dir: str | None) -> None:
    """Generate LaTeX output for all games, commentaries, harness, and figures.

    INPUT.yaml is the TeXFrog proof config file.
    """
    yaml_path = Path(input_yaml).resolve()
    if output_dir is None:
        out = yaml_path.parent / "texfrog_latex"
    else:
        out = Path(output_dir).resolve()

    click.echo(f"Parsing {yaml_path} …")
    try:
        proof = parse_proof(yaml_path)
    except Exception as exc:
        click.echo(f"Error parsing input: {exc}", err=True)
        sys.exit(1)
    _show_tag_warnings(proof)

    click.echo(f"Generating LaTeX in {out} …")
    try:
        generate_latex(proof, out)
    except Exception as exc:
        click.echo(f"Error generating LaTeX: {exc}", err=True)
        sys.exit(1)

    n_games = len(proof.games)
    n_figs = len(proof.figures)
    click.echo(
        f"Done. Wrote {n_games} game file(s), {n_figs} consolidated figure(s), "
        f"and proof_harness.tex in {out}/"
    )


# ---------------------------------------------------------------------------
# texfrog html
# ---------------------------------------------------------------------------

@main.group("html")
def html_group() -> None:
    """Build or serve the interactive HTML proof viewer."""


@html_group.command("build")
@click.argument("input_yaml", metavar="INPUT", type=click.Path(exists=True))
@click.option(
    "-o", "--output-dir",
    metavar="DIR",
    default=None,
    help="Output directory (default: texfrog_html/ next to INPUT.yaml).",
)
@click.option(
    "--keep-tmp",
    is_flag=True,
    default=False,
    help="Keep intermediate LaTeX/PDF files in a temp directory.",
)
def html_build_cmd(input_yaml: str, output_dir: str | None, keep_tmp: bool) -> None:
    """Build the interactive HTML proof viewer.

    INPUT is a proof YAML file or a directory containing proof.yaml.
    Requires pdflatex and pdf2svg (or pdftocairo) to be installed.
    """
    from .output.html import generate_html

    yaml_path = _resolve_yaml_path(input_yaml)
    if output_dir is None:
        out = yaml_path.parent / "texfrog_html"
    else:
        out = Path(output_dir).resolve()

    click.echo(f"Parsing {yaml_path} …")
    try:
        proof = parse_proof(yaml_path)
    except Exception as exc:
        click.echo(f"Error parsing input: {exc}", err=True)
        sys.exit(1)
    _show_tag_warnings(proof)

    click.echo(f"Building HTML site in {out} …")
    try:
        generate_html(proof, yaml_path.parent, out, keep_tmp=keep_tmp)
    except Exception as exc:
        click.echo(f"Error building HTML: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Done. Open {out / 'index.html'} in a browser.")


@html_group.command("serve")
@click.argument("input_yaml", metavar="INPUT", type=click.Path(exists=True))
@click.option(
    "-o", "--output-dir",
    metavar="DIR",
    default=None,
    help="Output directory (default: texfrog_html/ next to INPUT.yaml).",
)
@click.option("--port", default=8080, show_default=True, help="Port to listen on.")
@click.option("--no-browser", is_flag=True, default=False, help="Don't open a browser.")
@click.option(
    "--keep-tmp",
    is_flag=True,
    default=False,
    help="Keep intermediate LaTeX/PDF files in a temp directory.",
)
@click.option(
    "--live-reload",
    is_flag=True,
    default=False,
    help="Watch source files and rebuild/reload automatically on changes.",
)
def html_serve_cmd(
    input_yaml: str,
    output_dir: str | None,
    port: int,
    no_browser: bool,
    keep_tmp: bool,
    live_reload: bool,
) -> None:
    """Build and serve the interactive HTML proof viewer on localhost.

    INPUT is a proof YAML file or a directory containing proof.yaml.
    """
    from .output.html import generate_html, serve_html

    yaml_path = _resolve_yaml_path(input_yaml)
    if output_dir is None:
        out = yaml_path.parent / "texfrog_html"
    else:
        out = Path(output_dir).resolve()

    click.echo(f"Parsing {yaml_path} …")
    try:
        proof = parse_proof(yaml_path)
    except Exception as exc:
        click.echo(f"Error parsing input: {exc}", err=True)
        sys.exit(1)
    _show_tag_warnings(proof)

    click.echo(f"Building HTML site in {out} …")
    try:
        generate_html(proof, yaml_path.parent, out, keep_tmp=keep_tmp)
    except Exception as exc:
        click.echo(f"Error building HTML: {exc}", err=True)
        sys.exit(1)

    if live_reload:
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
            yaml_path, out, keep_tmp=keep_tmp,
            version=version, debounce_seconds=0.5,
        )
        try:
            serve_html_live(out, version, port=port, open_browser=not no_browser)
        finally:
            observer.stop()
            observer.join()
    else:
        serve_html(out, port=port, open_browser=not no_browser)
