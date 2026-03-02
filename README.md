# TeXFrog

> **Note:** TeXFrog is an early-stage tool under active development. The input format, command-line interface, and output may change as the design evolves. Feedback, suggestions, and contributions are very welcome — see [Contributing](#contributing) below.

> **Disclaimer:** Much of this codebase was vibe-coded with the assistance of large language models. While it has a test suite and works on the examples we have tried, there may be rough edges. Please report any issues you encounter.

TeXFrog helps cryptographers manage game-hopping proofs in LaTeX. If you have ever maintained a dozen nearly-identical game files by hand, copying lines between them and trying to keep highlights consistent, TeXFrog is meant to solve that problem.

**Key idea:** Write your pseudocode once in a single source file. Tag each line with the games it belongs to using `%:tags:` comments. TeXFrog produces:

- Individual per-game `.tex` files with changed lines automatically highlighted
- Consolidated comparison figures showing multiple games side by side
- An interactive HTML viewer for navigating the proof in a browser

All from that one source file.

TeXFrog currently supports the [`cryptocode`](https://ctan.org/pkg/cryptocode) and [`nicodemus`](https://github.com/awslabs/nicodemus) pseudocode packages.

## What It Looks Like

A snippet of the combined source file (`games_source.tex`):

```latex
k \getsr \{0,1\}^\lambda \\                      %:tags: G0-G2
...
y \gets \mathrm{PRF}(k, r) \\                    %:tags: G0
y \getsr \{0,1\}^\lambda \\                       %:tags: G1
y \gets \OPRF(r) \\                               %:tags: Red1
...
c \gets y \oplus m_b \\                           %:tags: G0,G1,Red1
c \getsr \{0,1\}^\lambda \\                       %:tags: G2
```

Lines with no `%:tags:` comment appear in every game. Lines with tags appear only in the listed games. Ranges like `G0-G2` are resolved by position in the game list, so reductions interleaved between games work naturally.

## Requirements

- **Python** >= 3.10
- **LaTeX** — [TeX Live](https://tug.org/texlive/) or [MacTeX](https://tug.org/mactex/) (for `pdflatex` and `pdfcrop`)
- **Poppler** — for `pdftocairo` (`brew install poppler` on macOS), or `pdf2svg` as an alternative

LaTeX and Poppler are only needed for the HTML viewer (`texfrog html`). The LaTeX output mode (`texfrog latex`) works with Python alone.

## Installation

```bash
git clone <repo-url>
cd TeXFrog
python3 -m venv .venv
source .venv/bin/activate    # on macOS/Linux; use .venv\Scripts\activate on Windows
pip install -e .
```

## Quick Start

The fastest way to start a new proof is with `texfrog init`:

```bash
# Scaffold a new proof in the current directory (cryptocode, the default)
texfrog init

# Or in a new directory, using the nicodemus package
texfrog init myproof --package nicodemus
```

This creates a minimal, runnable proof (`proof.yaml`, `games_source.tex`, and `macros.tex`) with comments explaining each field. Build it immediately:

```bash
texfrog latex proof.yaml -o /tmp/tf_output
```

TeXFrog also ships with tutorials you can study:

```bash
# Tutorial: IND-CPA proof (4 games/reductions)
texfrog latex tutorial-cryptocode/proof.yaml -o /tmp/tf_tutorial

# Same tutorial using the nicodemus package
texfrog latex tutorial-nicodemus/proof.yaml -o /tmp/tf_tutorial_nic

# Interactive HTML viewer with live reload
texfrog html serve tutorial-cryptocode/proof.yaml --live-reload
```

## Usage

### Scaffold a new proof

```bash
texfrog init [DIRECTORY] [--package cryptocode|nicodemus]
```

Creates starter files in DIRECTORY (default: current directory). The `--package` option selects the pseudocode package (default: `cryptocode`). Existing files are never overwritten.

### Validate a proof

```bash
texfrog check proof.yaml [--strict]
```

Parses the proof and runs all validation checks (YAML structure, file existence, tag consistency, empty games, commentary references) without generating any output. Prints a summary and exits with code 0 if valid. With `--strict`, exits with code 1 if there are any warnings.

### Generate LaTeX output

```bash
texfrog latex proof.yaml [-o OUTPUT_DIR]
```

Produces per-game `.tex` files, commentary files, a harness file, and consolidated figures. Output goes to `texfrog_latex/` next to the input file by default. See [LaTeX integration](docs/latex-integration.md) for how to incorporate the output into your paper.

### Build the HTML viewer

```bash
texfrog html build proof.yaml [-o OUTPUT_DIR]
```

Compiles each game to SVG via `pdflatex` and produces a self-contained HTML site. Open `index.html` in any browser. Games are shown side by side with changed lines highlighted, and you can navigate with arrow keys.

### Serve with live reload

```bash
texfrog html serve proof.yaml [--port 8080] [--live-reload]
```

Builds the HTML site, starts a local server, and opens your browser. With `--live-reload`, TeXFrog watches your source files and automatically rebuilds when you save changes.

## Writing a Proof

You need two input files:

- **`proof.yaml`** — declares the list of games and reductions, points to your macro files and source, and optionally specifies commentary, figures, and which pseudocode package to use
- **`games_source.tex`** — the single combined LaTeX source file with `%:tags:` annotations

See [Writing a proof](docs/writing-proofs.md) for a full guide, and the [tutorials](#included-examples) for worked examples.

## Included Examples

| Directory | Description | Package |
|-----------|-------------|---------|
| [`tutorial-cryptocode/`](tutorial-cryptocode/) | Small IND-CPA proof walkthrough (4 games/reductions) | `cryptocode` |
| [`tutorial-nicodemus/`](tutorial-nicodemus/) | Same proof using `nicodemus` syntax | `nicodemus` |

Comparing the two tutorials side by side shows the syntax differences between pseudocode packages.

## Documentation

- [Writing a proof](docs/writing-proofs.md) — `proof.yaml` and `games_source.tex` reference
- [Using TeXFrog Output in Your LaTeX Paper](docs/latex-integration.md) — incorporating output into your paper, customizing highlight macros
- [Troubleshooting & FAQ](docs/troubleshooting.md) — common problems proof authors encounter

## Contributing

TeXFrog is in its early stages and we are actively looking for feedback from cryptographers who write game-hopping proofs. If you try TeXFrog on your own proof and run into rough edges, have ideas for features, or want to contribute code, please open an issue or pull request. Your input will help shape the tool into something genuinely useful for the community.

To set up a development environment:

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

## License

TBD
