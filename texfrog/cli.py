"""TeXFrog command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .parser import parse_proof
from .output.latex import generate_latex


@click.group()
def main() -> None:
    """TeXFrog: organise and render cryptographic game-hopping proofs in LaTeX."""


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
@click.argument("input_yaml", metavar="INPUT.yaml", type=click.Path(exists=True, dir_okay=False))
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

    Requires pdflatex and pdf2svg (or pdftocairo) to be installed.
    """
    from .output.html import generate_html

    yaml_path = Path(input_yaml).resolve()
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

    click.echo(f"Building HTML site in {out} …")
    try:
        generate_html(proof, yaml_path.parent, out, keep_tmp=keep_tmp)
    except Exception as exc:
        click.echo(f"Error building HTML: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Done. Open {out / 'index.html'} in a browser.")


@html_group.command("serve")
@click.argument("input_yaml", metavar="INPUT.yaml", type=click.Path(exists=True, dir_okay=False))
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
def html_serve_cmd(
    input_yaml: str,
    output_dir: str | None,
    port: int,
    no_browser: bool,
    keep_tmp: bool,
) -> None:
    """Build and serve the interactive HTML proof viewer on localhost."""
    from .output.html import generate_html, serve_html

    yaml_path = Path(input_yaml).resolve()
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

    click.echo(f"Building HTML site in {out} …")
    try:
        generate_html(proof, yaml_path.parent, out, keep_tmp=keep_tmp)
    except Exception as exc:
        click.echo(f"Error building HTML: {exc}", err=True)
        sys.exit(1)

    serve_html(out, port=port, open_browser=not no_browser)
