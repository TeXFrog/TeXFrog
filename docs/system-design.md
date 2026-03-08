# TeXFrog Design Document

This document captures the architecture, key algorithms, design decisions, and important
implementation gotchas for contributors and maintainers.

---

## Purpose

TeXFrog is a tool for cryptographers who write game-hopping proofs in LaTeX.
It has two components:

1. **`texfrog.sty`** — a standalone LaTeX3 (expl3) package that handles game filtering,
   automatic diff highlighting, and consolidated figures entirely at compile time.
   Authors use `\tfonly{tags}{content}` macros inside a `\begin{tfsource}` environment,
   then render individual games with `\tfrendergame` and figures with `\tfrenderfigure`.

2. **Python CLI tool** — reads the same `.tex` file and builds an interactive HTML site
   (via pdflatex → pdftocairo → SVG) with side-by-side game comparison, commentary,
   MathJax rendering, and live-reload.

The `.tex` file is the **single source of truth** for both LaTeX compilation and HTML
export. A legacy YAML input format is also supported for backward compatibility.

The tool supports multiple LaTeX pseudocode packages via a **package profile** system.
Currently supported: `cryptocode` (default) and `nicodemus`. Each profile captures
differences in line separators, content mode, and macro definitions.

---

## Project Structure

```
TeXFrog/
├── pyproject.toml              # setuptools.build_meta; include = ["texfrog*"] only
├── latex/
│   └── texfrog.sty             # Pure LaTeX3 package for compile-time game rendering
├── texfrog/
│   ├── __init__.py
│   ├── model.py                # Dataclasses: Proof, Game, SourceLine, Figure
│   ├── tex_parser.py           # Parse .tex files with TeXFrog commands (preferred)
│   ├── parser.py               # YAML + tagged .tex parsing (legacy), range resolution
│   ├── filter.py               # Line filtering, diff, \tfchanged wrapping
│   ├── packages.py             # PackageProfile dataclass + built-in profiles
│   ├── validate.py             # Proof validation checks
│   ├── cli.py                  # Click CLI: texfrog init / check / html build / html serve
│   ├── templates.py            # Inline template strings for texfrog init
│   ├── watcher.py              # File watching + safe rebuild for live-reload
│   └── output/
│       ├── __init__.py
│       ├── latex.py            # generate_latex(): per-game .tex, commentary, harness, figures
│       └── html.py             # generate_html() + serve_html(): pdflatex → SVG → HTML site
├── tests/
│   ├── fixtures/simple/        # Minimal cryptocode YAML + source.tex for fast unit tests
│   ├── fixtures/nicodemus/     # Minimal nicodemus YAML + source.tex for package tests
│   ├── test_tex_parser.py      # Tests for .tex format parsing
│   ├── test_parser.py          # Tests for YAML format parsing
│   ├── test_filter.py
│   └── test_latex_output.py
├── examples/
│   ├── tutorial-pure-latex/    # IND-CPA tutorial using pure LaTeX format (preferred)
│   │   ├── main.tex            # Complete document with TeXFrog commands
│   │   └── macros.tex          # Custom macros
│   ├── tutorial-cryptocode/    # IND-CPA tutorial (YAML format, cryptocode)
│   ├── tutorial-nicodemus/     # IND-CPA tutorial (YAML format, nicodemus)
│   └── example-compositekems/  # QSH IND-CCA proof (YAML format, cryptocode)
└── CompositeKEMs/              # Reference only — NOT part of the Python package
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
    related_games: list[str] = field(default_factory=list)  # 0–2 game labels shown alongside this reduction

@dataclass
class SourceLine:
    content: str                   # Line with %:tags: comment stripped
    tags: Optional[frozenset[str]] # None = all games; set = only these labels
    original: str                  # Raw original line (for debugging)

@dataclass
class Figure:
    label: str        # e.g. "start_end" → output file fig_start_end.tex
    games: list[str]  # Ordered game labels to include (ordered per proof.games)
    procedure_name: Optional[str] = None  # Custom title for the first procedure header

@dataclass
class Proof:
    macros: list[str]              # Paths relative to the input file
    games: list[Game]              # All games/reductions in declared order
    source_lines: list[SourceLine] # All lines from combined source (YAML format)
    commentary: dict[str, str]     # label → LaTeX text (loaded from files)
    figures: list[Figure]          # Consolidated figure specs
    package: str = "cryptocode"    # Package profile name (see packages.py)
    preamble: Optional[str] = None # Path to extra preamble .tex (relative to input dir)
    commentary_files: dict[str, str] = field(default_factory=dict)  # label → relative file path
    source_text: Optional[str] = None  # Raw tfsource body (.tex format; None for YAML)
```

---

## Input Format

### Pure LaTeX Format (Preferred)

The `.tex` file is the single source of truth. It uses `texfrog.sty` for compile-time
rendering and is parsed by `texfrog/tex_parser.py` for HTML export.

```latex
\usepackage{texfrog}

% Game registration (order determines range resolution)
\tfgames{G0, G1, Red1, G2}
\tfgamename{G0}{G_0}
\tfgamename{Red1}{\Bdversary_1}
\tfdescription{G0}{The starting game.}
\tfreduction{Red1}
\tfrelatedgames{Red1}{G0, G1}

% Metadata for Python HTML export (no-ops in LaTeX)
\tfsetpackage{cryptocode}
\tfmacrofile{macros.tex}
\tfcommentary{G0}{commentary/G0.tex}

% Proof source with \tfonly{tags}{content} filtering
\begin{tfsource}{myproof}
\begin{pcvstack}[boxed]
  \procedure[linenumbering]{%
    \tfonly{G0}{Game $\tfgamename{G0}$}%
    \tfonly{G1}{Game $\tfgamename{G1}$}%
  }{
    \tfonly{G0}{k \sample \{0,1\}^\lambda \\}
    b' \gets \Adversary(y) \\
    \pcreturn b'
  }
\end{pcvstack}
\end{tfsource}

% Rendering
\tfrendergame{myproof}{G0}                    % no highlighting (first game)
\tfrendergame{myproof}{G1}                    % auto-highlighted changes
\tfrendergame[highlight=false]{myproof}{G1}   % clean, no highlighting
\tfrenderfigure{myproof}{G0,G1,G2}            % consolidated figure
```

**`\tfonly{tags}{content}`** — content appears only in the listed games:
- `\tfonly{G1}{...}` — only in G1
- `\tfonly{G0,G2}{...}` — in G0 and G2
- `\tfonly{G0-G2}{...}` — in all games from G0 to G2 by position

**`\tfonly*{tags}{content}`** — like `\tfonly` but suppressed in consolidated
figures (`\tfrenderfigure`). Use for per-game procedure headers that should not
appear in the combined view.

**`\tffigonly{content}`** — shown only in consolidated figures, hidden in
single-game rendering. Use for a combined header in `\tfrenderfigure` output.

Typical pattern for procedure headers:
```latex
\procedure[linenumbering]{%
  \tfonly*{G0}{Game $\tfgamename{G0}$}%
  \tfonly*{G1}{Game $\tfgamename{G1}$}%
  \tffigonly{Games $\tfgamename{G0}$--$\tfgamename{G1}$}%
}{...}
```

### YAML Format (Legacy)

### `proof.yaml`

```yaml
package: cryptocode            # or "nicodemus" (default: "cryptocode")

macros:
  - macros.tex                 # relative to this yaml file
  - nicodemus.sty              # .sty files are copied but not \input'd

preamble: preamble.tex         # optional: extra \usepackage lines for HTML build

source: games_source.tex       # relative to this yaml file

games:
  - label: G0
    latex_name: '\indcca_\QSH^\adv.\REAL()'
    description: 'The starting game (real IND-CCA game).'
  - label: G1
    latex_name: 'G_1'
    description: 'Replace $\key_2$ with a fresh $\key_2^*$.'
  - label: Red2
    latex_name: '\bdv_2'
    description: 'Reduction against $\indcca$ security of $\KEM_2$.'
    reduction: true
    related_games: [G0, G1]      # show clean G0 and G1 alongside in HTML viewer
  # ... more games ...

commentary:                    # optional; values are file paths relative to this yaml file
  G0: commentary/G0.tex
  G1: commentary/G1.tex

figures:                       # optional
  - label: start_end
    games: "G0,G9"
    procedure_name: "Games $G_0$--$G_9$"   # custom title for first procedure header
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
- **Lines with `\item` prefix** (nicodemus-style): `\item` is placed OUTSIDE the macro:
  `\item \tfchanged{content}` to preserve list structure.
- **Other lines**: `\tfchanged{line}` directly.

---

## LaTeX Output (`output/latex.py`)

### Per-game files: `{label}.tex`

Generated by `_write_game_file`. Contains filtered content with changed lines wrapped
in `\tfchanged{}`. **Blank/whitespace-only lines are skipped** — they arise from
excluded tagged content and cause `varwidth` dimension errors inside pseudocode
environments like cryptocode's `pcvstack`.

### Commentary files: `{label}_commentary.tex`

Generated only if commentary text is non-empty. Contains the content loaded from the
corresponding commentary file (e.g., `commentary/G0.tex` as specified in proof.yaml).

### Harness: `proof_harness.tex`

- Defines `\tfchanged` (via `\providecommand`), `\tfgamelabel`, and `\tfgamename`
- `\tfgamename{label}` expands to `\ensuremath{latex_name}` via `\@namedef`/`\@nameuse`
- `\input`s each macro file (`.sty`/`.cls` files are skipped — they are loaded via `\usepackage`)
- `\input`s each game file, then its commentary file, in order

The `\providecommand` means authors can override macros in their paper preamble.
Default `\tfchanged` varies by package: `\colorbox{blue!15}{$#1$}` for cryptocode (math mode),
`\colorbox{blue!15}{#1}` for nicodemus (text mode).

### Consolidated figures: `fig_{label}.tex`

For each source line:
- In ALL selected games → output verbatim
- In SUBSET of selected games → `\tfgamelabel{\tfgamename{G1},\tfgamename{G3}}{line content}`
- In NO selected games → skip

If `procedure_name` is set on the figure, the title of the first procedure header
in the output is replaced with the given text. This lets consolidated figures show
e.g. "Games $G_0$--$G_9$" instead of the first game's specific header. Subsequent
procedure headers (e.g. oracle definitions) are unaffected.

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

The `\tfchanged` macro in the HTML wrapper varies by package profile:
- **cryptocode** (math-mode content): Uses `\ifmmode` to detect context — wraps with
  `\ensuremath` inside `\highlightbox` when in math mode, plain `\highlightbox` in text mode.
  This is necessary because procedure titles are text-mode while procedure bodies are
  math-mode in cryptocode's `\procedure` environment.
- **nicodemus** (text-mode content): `\newcommand{\tfchanged}[1]{\highlightbox{#1}}`

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
    ├── G0-clean.svg         # clean version (no highlighting; only for related_games targets)
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
appears as a "previous" game. Games referenced by a reduction's `related_games` also
get a third "clean" compilation with no highlighting, used in the reduction's display.

HTML features: MathJax for LaTeX names and descriptions, URL hash navigation (`#G1`),
keyboard arrows, commentary rendered as SVG via the LaTeX pipeline, prev/next buttons,
side-by-side game comparison.

### Side-by-Side Display

After the first game, the HTML viewer shows the previous game (with red strikethrough
on lines that are removed or changed) next to the current game (with blue highlights
on new/changed lines), making it easy to see what changed between game transitions.

Reductions support a `related_games` field listing zero, one, or two game labels:
- **0 related games**: the reduction is shown alone (legacy behaviour).
- **1 related game**: the clean game appears on the left, the highlighted reduction
  on the right.
- **2 related games**: the first clean game on the left, the highlighted reduction in
  the middle, the second clean game on the right.

### Live Reload (`watcher.py` + `output/html.py`)

When `--live-reload` is passed to `html serve`, the tool watches the proof's source
files (input .tex or YAML, macros, preamble, commentary files) using `watchdog`
and automatically rebuilds + reloads the browser on changes.

**File watching** (`watcher.py`):
- `collect_watched_files(input_path)` discovers files to watch. For `.tex` input, it
  scans for `\tfmacrofile`, `\tfpreamble`, `\tfcommentary`, and `\input` commands.
  For YAML input, it reads the YAML with `yaml.safe_load`.
- `_DebouncedHandler` ignores events for files not in the watched set and debounces
  rapid changes (0.5 s quiet period) before triggering a rebuild.
- `safe_rebuild()` builds into a staging temp dir (created in `output_dir.parent` to
  guarantee same-filesystem). On success, the old output dir is atomically swapped via
  rename. On failure, the existing site is left untouched and the error is logged.
- After each successful rebuild, the watched file set is refreshed from the input file
  in case it changed (e.g. a new macro file was added).

**Browser reload** (`output/html.py`):
- `serve_html_live()` uses a custom `LiveReloadHandler` subclass that adds a
  `/_texfrog/version` JSON endpoint returning `{"version": N}`.
- A small inline `<script>` is injected into `index.html` at serve time (not at build
  time — `generate_html` output is unaffected). The script polls the version endpoint
  every 1 second and calls `location.reload()` when the version changes.
- On reload, a toast notification appears in the bottom-right corner showing the
  timestamp (e.g. "Reloaded at 14:32:05"), with a close button and 10-second auto-dismiss.
  The toast uses `sessionStorage` to pass the "just reloaded" flag across the page reload.
- All responses include `Cache-Control: no-store` so the browser always fetches fresh
  SVGs after a rebuild. Version endpoint polls are suppressed from the server's terminal
  log output.

---

## CLI (`cli.py`)

Built with Click. Entry point: `texfrog` → `texfrog.cli:main`.

```
texfrog init [DIRECTORY] [--package cryptocode|nicodemus]
texfrog check INPUT [--strict]
texfrog html build INPUT [-o DIR] [--keep-tmp]
texfrog html serve INPUT [-o DIR] [--port 8080] [--no-browser] [--live-reload]
```

INPUT can be a `.tex` file with TeXFrog commands (preferred), a `.yaml` file (legacy),
or a directory containing `proof.tex` (or `proof.yaml` as fallback).

### `texfrog init`

Scaffolds a new proof directory with a `proof.tex` file containing TeXFrog commands,
a `macros.tex` file, and a `commentary/` subdirectory with starter commentary files.
The `--package` option selects the template flavour (default: `cryptocode`).
Existing files are never overwritten — skipped with a warning instead.

Templates are stored as inline strings in `texfrog/templates.py`. Each template set
produces a minimal 4-game proof that is immediately compilable with `pdflatex`.

Default output dir: `texfrog_html/` next to the input file.

---

## Development Setup

```bash
cd TeXFrog/
python3 -m venv .venv
source .venv/bin/activate   # or: .venv/bin/activate.fish for fish shell
pip install -e ".[dev]"     # installs texfrog + pytest
texfrog --help
pytest tests/ -q            # 269 tests
```

System requirements (not pip-installable):
- `pdflatex` — from TeX Live / MacTeX
- `pdftocairo` — from poppler (via `brew install poppler` on macOS), OR `pdf2svg`
- `pdfcrop` — from TeX Live (optional but recommended for clean SVG cropping)

---

## Tutorials and Example Proofs

### `examples/tutorial-pure-latex/` — IND-CPA (pure LaTeX format, preferred)

Implements a small IND-CPA proof (5 entries: G0, G1, Red1, G2, G3) using the pure LaTeX
format with `texfrog.sty`. The `.tex` file is the single source of truth — it compiles
directly with `pdflatex` and can also be used with `texfrog html build` for the HTML viewer.

### `examples/tutorial-cryptocode/` and `examples/tutorial-nicodemus/` — IND-CPA (YAML format)

Legacy YAML-format tutorials implementing the same small IND-CPA proof (4 entries: G0,
G1, Red1, G2). `tutorial-cryptocode/` uses `package: cryptocode` (default);
`tutorial-nicodemus/` uses `package: nicodemus`.

### `examples/example-compositekems/` — QSH IND-CCA (YAML format, cryptocode)

A larger YAML-format example with 12 entries: G0–G9, Red2, Red5.

---

## Package Profiles (`packages.py`)

Package-specific behavior is abstracted via `PackageProfile`:

| Attribute | cryptocode | nicodemus |
|-----------|-----------|-----------|
| `has_line_separators` | `True` (`\\` between lines) | `False` (`\item` per line) |
| `math_mode_content` | `True` (inside `\procedure`) | `False` (inside `\begin{nicodemus}`) |
| `gamelabel_comment_cmd` | `\pccomment` | `None` |

Derived methods generate `\tfchanged`, `\tfremoved`, and `\tfgamelabel` definitions
appropriate for each package, used in both the LaTeX harness and HTML wrapper.

`.sty`/`.cls` files in the `macros:` list are handled specially: they are copied to
the build directory without renaming (so `\usepackage` can find them) and are NOT
`\input`'d in the harness.

---

## Known Limitations / Future Work

- No validation that game labels in `%:tags:` comments actually exist in the YAML
  (unknown labels are silently ignored)
