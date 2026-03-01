# TeXFrog Design Document

This document is written for Claude instances working on this codebase. It captures the
architecture, key algorithms, design decisions, and important implementation gotchas.

---

## Purpose

TeXFrog is a Python tool for cryptographers who write game-hopping proofs in LaTeX.
The core innovation is a **single combined LaTeX source file** where each line is
optionally tagged with `%:tags:` comments indicating which games/reductions it belongs
to. The tool then:

1. Filters lines per game to produce individual per-game `.tex` files
2. Diffs adjacent games and highlights changed lines with `\tfchanged{}`
3. Produces consolidated figures showing multiple games annotated side-by-side
4. Builds an interactive HTML site (via pdflatex → pdftocairo → SVG)

The tool is pseudocode-package-agnostic: it works with `cryptocode`, `algorithmic`,
`algpseudocode`, etc., since it operates at the level of physical lines.

---

## Project Structure

```
TeXFrog/
├── pyproject.toml              # setuptools.build_meta; include = ["texfrog*"] only
├── texfrog/
│   ├── __init__.py
│   ├── model.py                # Dataclasses: Proof, Game, SourceLine, Figure
│   ├── parser.py               # YAML + tagged .tex parsing, range resolution
│   ├── filter.py               # Line filtering, diff, \tfchanged wrapping
│   ├── cli.py                  # Click CLI: texfrog latex / html build / html serve
│   └── output/
│       ├── __init__.py
│       ├── latex.py            # generate_latex(): per-game .tex, commentary, harness, figures
│       └── html.py             # generate_html() + serve_html(): pdflatex → SVG → HTML site
├── tests/
│   ├── fixtures/simple/        # Minimal YAML + source.tex for fast unit tests
│   ├── test_parser.py          # 20 tests: tag parsing, range resolution, full parse_proof
│   ├── test_filter.py          # 16 tests: filter_for_game, compute_changed_lines, wrap_changed_line
│   └── test_latex_output.py    # 20 tests: per-game files, harness, consolidated figures
├── example/
│   ├── proof.yaml              # QSH IND-CCA proof config (12 games/reductions)
│   └── games_source.tex        # Combined tagged source for the example
└── CompositeKEMs/              # Reference only — NOT part of the Python package
    ├── simple_extract.tex      # Original 562-line proof (reference/inspiration)
    └── macros.tex              # Crypto macros used by the example
```

**Important**: `pyproject.toml` must have `[tool.setuptools.packages.find]` with
`include = ["texfrog*"]` to prevent `CompositeKEMs/` being detected as a Python package.

---

## Data Model (`model.py`)

```python
@dataclass
class Game:
    label: str        # e.g. "G0", "Red2" — used as filename stem and hash anchor
    latex_name: str   # Math-mode content without $ delimiters, e.g. r'\indcca_\QSH^\adv.\REAL()'
    description: str  # One-sentence LaTeX description (shown in HTML sidebar)
    reduction: bool = False  # True for reductions (displayed alone in HTML, not side-by-side)

@dataclass
class SourceLine:
    content: str                   # Line with %:tags: comment stripped
    tags: Optional[frozenset[str]] # None = all games; set = only these labels
    original: str                  # Raw original line (for debugging)

@dataclass
class Figure:
    label: str        # e.g. "start_end" → output file fig_start_end.tex
    games: list[str]  # Ordered game labels to include (ordered per proof.games)

@dataclass
class Proof:
    macros: list[str]              # Paths relative to the yaml file
    games: list[Game]              # All games/reductions in declared order
    source_lines: list[SourceLine] # All lines from combined source
    commentary: dict[str, str]     # label → raw LaTeX text
    figures: list[Figure]          # Consolidated figure specs
```

---

## Input Format

### `proof.yaml`

```yaml
macros:
  - macros.tex                 # relative to this yaml file

source: games_source.tex       # relative to this yaml file

games:
  - label: G0
    latex_name: '\indcca_\QSH^\adv.\REAL()'
    description: 'The starting game (real IND-CCA game).'
  - label: G1
    latex_name: 'G_1'
    description: 'Replace $\key_2$ with a fresh $\key_2^*$.'
  # ... more games ...

commentary:                    # optional
  G0: |
    The starting game is the real IND-CCA experiment.
  G1: |
    \begin{claim} Games 0 and 1 are indistinguishable ... \end{claim}

figures:                       # optional
  - label: start_end
    games: "G0,G9"
  - label: game2_reduction
    games: "G1-Red2"           # range: all games from G1 to Red2 inclusive
```

### `games_source.tex` — Tag Syntax

```latex
% Lines with no %:tags: comment appear in EVERY game/reduction:
(\pk_1, \sk_1) \getsr \KEM_1.\keygen() \\

% Lines tagged for specific games only:
(\ct_1^*, \key_1) \getsr \KEM_1.\encaps(\pk_1) \\   %:tags: G0-G3,Red2
(\ct_1^*, \key_1^*) \getsr \KEM_1.\encaps(\pk_1) \\ %:tags: G4,G5,Red5
(\ct_1^*, \_\_) \getsr \KEM_1.\encaps(\pk_1) \\      %:tags: G6-G9
```

**Tag semantics:**
- `%:tags: G1` — only in G1
- `%:tags: G0,G3-G5` — in G0, G3, G4, G5
- `%:tags: G0-G9` — in every label from G0 to G9 *by position in the games list*
- No `%:tags:` → in all games

**Range resolution** is **positional**, not alphabetical or numerical. The game list
order in the YAML determines what "G0-G5" means. This allows labels like "Red2" to sit
between G1 and G3 in the sequence without breaking range syntax.

**CRITICAL source ordering constraint**: Variant lines for the same "slot" (e.g.,
alternative encaps lines for different games) MUST be consecutive in the source file.
The tool filters but does NOT reorder. Put all G0-only, then G1-only, then shared
versions of the same logical line in sequence.

---

## Core Algorithms

### 1. Tag Range Resolution (`parser.py: resolve_tag_ranges`)

Given `ordered_labels = ["G0","G1","G2","Red2","G3",...]` and `"G0,G3-G5"`:
- Split on `,`
- For tokens containing `-`: try splitting at each `-` to find two valid labels
- Resolve range to all labels between start and end (inclusive) by position
- Unknown single labels are kept verbatim (silently ignored at filter time)

### 2. Line Filtering (`filter.py: filter_for_game`)

```python
def filter_for_game(source_lines, label):
    included = [sl.content for sl in source_lines
                if sl.tags is None or label in sl.tags]
    return _strip_trailing_newline_sep(included)
```

After filtering, the last non-empty line may end with `\\` (cryptocode line separator
that's only needed between lines, not after the last one). `_strip_trailing_newline_sep`
removes trailing `\\` from the last non-empty line. This is a no-op for packages that
don't use `\\` (algorithmicx etc.).

### 3. Diff Computation (`filter.py: compute_changed_lines`)

Uses `difflib.SequenceMatcher` to align the previous game's filtered lines with the
current game's filtered lines. Returns a `set[int]` of 0-based indices into the
current lines that are insertions or replacements (not in the previous game).

The first game (index 0) always gets an empty changed set.

### 4. Change Highlighting (`filter.py: wrap_changed_line`)

Wraps a changed line in `\tfchanged{content}`, with special handling:

- **Lines ending with `{`** (procedure headers like `\procedure{Name}{`): NOT wrapped —
  wrapping would break LaTeX brace matching since the `{` opens the procedure body.
- **Pure comment lines** (starting with `%` after stripping): NOT wrapped — invisible
  in PDF, wrapping produces spurious output.
- **Lines with trailing `\\`** (cryptocode separator): `\\` is placed OUTSIDE the macro:
  `\tfchanged{content} \\` so the separator stays at the token level.
- **Other lines**: `\tfchanged{line}` directly.

---

## LaTeX Output (`output/latex.py`)

### Per-game files: `{label}.tex`

Generated by `_write_game_file`. Contains filtered content with changed lines wrapped
in `\tfchanged{}`. **Blank/whitespace-only lines are skipped** — they arise from
excluded tagged content and cause `varwidth` dimension errors inside pseudocode
environments like cryptocode's `pcvstack`.

### Commentary files: `{label}_commentary.tex`

Generated only if commentary text is non-empty. Contains verbatim YAML commentary.

### Harness: `proof_harness.tex`

- Defines `\tfchanged` (via `\providecommand`), `\tfgamelabel`, and `\tfgamename`
- `\tfgamename{label}` expands to `\ensuremath{latex_name}` via `\@namedef`/`\@nameuse`
- `\input`s each macro file
- `\input`s each game file, then its commentary file, in order

The `\providecommand` means authors can override macros in their paper preamble.
Default `\tfchanged`: `\colorbox{blue!15}{$#1$}` (works in math mode).

### Consolidated figures: `fig_{label}.tex`

For each source line:
- In ALL selected games → output verbatim
- In SUBSET of selected games → `\tfgamelabel{\tfgamename{G1},\tfgamename{G3}}{line content}`
- In NO selected games → skip

---

## HTML Output (`output/html.py`)

### Pipeline

For each game:
1. Generate per-game `.tex` via `generate_latex` (in a temp dir)
2. Copy game `.tex` and all macro files to a **flat temp directory with no spaces in path**
   (LaTeX's `\input{}` cannot handle paths with spaces — the project lives in
   "Formal methods/" which has a space)
3. Write a wrapper `.tex` with full preamble + `\input{game.tex}`
4. Run `pdflatex -interaction=nonstopmode wrapper.tex`
5. Run `pdfcrop` (if available) to strip whitespace margins
6. Run `pdftocairo -svg` (or `pdf2svg`) to produce the SVG

### Wrapper Template Preamble

Uses `\documentclass{article}` with `[letterpaper,margin=1in]{geometry}`.

**DO NOT use** `standalone` class — it runs in LR mode, incompatible with `pcvstack`.
**DO NOT use** `\usepackage[active,tightpage]{preview}` — conflicts with `varwidth`
(used internally by cryptocode's `pcvstack`), causing "Dimension too large" errors.

The `\tfchanged` macro in the HTML wrapper MUST use `\ensuremath`:
```latex
\newcommand{\tfchanged}[1]{\highlightbox{\ensuremath{#1}}}
```
Because `\adjustbox` (used by `\highlightbox`) processes content in text mode, but
pseudocode content contains math-mode macros like `\mathsf`, `\mathcal`, etc.
Without `\ensuremath`, you get "! LaTeX Error: \mathsf allowed only in math mode."

### pdftocairo Behavior

`pdftocairo -svg input.pdf output.svg` writes to the **exact filename** specified —
it does NOT append `.svg`. Pass the full `.svg` path directly.

Commentary is also compiled through the same pipeline, producing `{label}_commentary.svg`
files for each game that has commentary text. The wrapper preamble includes `\tfgamename`
definitions so that commentary can reference game names. Any other commands or environments
used in commentary (e.g., `\newtheorem{claim}{Claim}`) must be defined in the user's
macros file.

### Site Structure

```
output_dir/
├── index.html       # navigation sidebar + game viewer
├── style.css
├── app.js           # showGame(), navigate(), keyboard nav (arrow keys)
└── games/
    ├── G0.svg               # highlighted version (blue on new/changed lines)
    ├── G0-removed.svg       # removed version (red strikethrough on deleted/changed lines)
    ├── G0_commentary.svg    # rendered commentary (only if commentary was provided)
    ├── G1.svg
    ├── G1-removed.svg
    ├── G1_commentary.svg
    └── ...
```

Each game is compiled twice: once with `\tfchanged` highlighting (blue, for the
current-game panel) and once with `\tfremoved` highlighting (red strikethrough, for
the previous-game panel in side-by-side view showing lines that will be removed or
changed in the next game). The last game does not need a removed SVG since it never
appears as a "previous" game.

HTML features: MathJax for LaTeX names and descriptions, URL hash navigation (`#G1`),
keyboard arrows, commentary rendered as SVG via the LaTeX pipeline, prev/next buttons,
side-by-side game comparison.

### Side-by-Side Display

After the first game, the HTML viewer shows the previous game (with red strikethrough
on lines that are removed or changed) next to the current game (with blue highlights
on new/changed lines), making it easy to see what changed between game transitions.
Reductions (games with `reduction: true` in the YAML) are shown alone, not
side-by-side.

---

## CLI (`cli.py`)

Built with Click. Entry point: `texfrog` → `texfrog.cli:main`.

```
texfrog latex INPUT.yaml [-o DIR]
texfrog html build INPUT.yaml [-o DIR]
texfrog html serve INPUT.yaml [-o DIR] [--port 8080] [--no-browser]
```

Default output dirs: `texfrog_latex/` (latex) and `texfrog_html/` (html), both
created next to the input YAML file.

---

## Development Setup

```bash
cd TeXFrog/
python3 -m venv .venv
source .venv/bin/activate   # or: .venv/bin/activate.fish for fish shell
pip install -e ".[dev]"     # installs texfrog + pytest
texfrog --help
pytest tests/ -q            # 56 tests
```

System requirements (not pip-installable):
- `pdflatex` — from TeX Live / MacTeX
- `pdftocairo` — from poppler (via `brew install poppler` on macOS), OR `pdf2svg`
- `pdfcrop` — from TeX Live (optional but recommended for clean SVG cropping)

---

## Example Proof

`example/proof.yaml` + `example/games_source.tex` implements the QSH IND-CCA proof
from `CompositeKEMs/simple_extract.tex`, with 12 entries: G0–G9, Red2, Red5.
Each game and reduction is separate (no side-by-side layout in a single file).

The source file uses `\begin{pcvstack}[boxed]` with two `\procedure` environments
(main body + oracle). The oracle uses both compact (G0–G2, G8–G9) and expanded
case-decomposition (G3–G7) forms, interleaved with proper ordering.

---

## Known Limitations / Future Work

- The consolidated figure output (`fig_*.tex`) does not handle the `\\` separator
  stripping correctly for the annotated lines — this may need attention if the
  annotated lines end with `\\`
- No validation that game labels in `%:tags:` comments actually exist in the YAML
  (unknown labels are silently ignored)
