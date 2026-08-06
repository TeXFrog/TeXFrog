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
export.

The tool supports multiple LaTeX pseudocode packages via a **package profile** system.
Currently supported: `cryptocode` (default), `nicodemus`, and `algpseudocodex`.
Each profile captures
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
│   ├── model.py                # Dataclasses: Proof, Game, Figure
│   ├── tex_parser.py           # Parse .tex files with TeXFrog commands
│   ├── filter.py               # Line filtering, diff, \tfchanged wrapping
│   ├── packages.py             # PackageProfile dataclass + built-in profiles
│   ├── validate.py             # Proof validation checks
│   ├── cli.py                  # Click CLI: texfrog init / check / html build / html serve
│   ├── templates.py            # Inline template strings for texfrog init
│   ├── watcher.py              # File watching + safe rebuild for live-reload
│   └── output/
│       ├── __init__.py
│       └── html.py             # generate_html() + serve_html(): per-game .tex, pdflatex → SVG → HTML site
├── tests/
│   ├── test_tex_parser.py      # Tests for .tex format parsing
│   ├── test_filter.py          # Line filtering, diff, \tfchanged wrapping
│   ├── test_latex_output.py    # LaTeX output generation
│   ├── test_packages.py        # Package profile tests
│   ├── test_validate.py        # Proof validation checks
│   ├── test_html_internals.py  # HTML generation internals
│   ├── test_html_viewer.py     # HTML viewer integration tests
│   ├── test_check_cli.py       # texfrog check CLI tests
│   ├── test_cli_helpers.py     # CLI helper function tests
│   ├── test_init.py            # texfrog init scaffolding tests
│   ├── test_integration.py     # End-to-end integration tests
│   ├── test_watcher.py         # File watcher tests
│   ├── test_sty_compilation.py # texfrog.sty LaTeX compilation tests
│   └── test_deps.py            # Dependency detection tests
├── examples/
│   ├── tutorial-cryptocode-quickstart/    # IND-CPA tutorial using pure LaTeX format
│   │   ├── main.tex            # Complete document with TeXFrog commands
│   │   └── macros.tex          # Custom macros
│   ├── tutorial-cryptocode/    # IND-CPA tutorial (pure LaTeX format, cryptocode)
│   ├── tutorial-nicodemus/     # IND-CPA tutorial (pure LaTeX format, nicodemus)
│   ├── tutorial-algpseudocodex/ # IND-CPA tutorial (pure LaTeX format, algpseudocodex)
│   └── example-multiproof/     # Multiple proofs in a single document
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
class Figure:
    label: str        # e.g. "start_end" → output file fig_start_end.tex
    games: list[str]  # Ordered game labels to include (ordered per proof.games)
    procedure_name: Optional[str] = None  # Custom title for the first procedure header

@dataclass
class Proof:
    source_name: str               # Name from \begin{tfsource}{name}
    macros: list[str]              # Paths relative to the input file
    games: list[Game]              # All games/reductions in declared order
    source_text: str               # Raw tfsource body (\tfonly format)
    commentary: dict[str, str]     # label → LaTeX text (loaded from files)
    figures: list[Figure]          # Consolidated figure specs
    package: str = "cryptocode"    # Package profile name (see packages.py)
    preamble: Optional[str] = None # Path to extra preamble .tex (relative to input dir)
    commentary_files: dict[str, str] = field(default_factory=dict)  # label → relative file path
```

---

## Input Format

### Pure LaTeX Format (Preferred)

The `.tex` file is the single source of truth. It uses `texfrog.sty` for compile-time
rendering and is parsed by `texfrog/tex_parser.py` for HTML export.

```latex
\usepackage[package=cryptocode]{texfrog}

% Game registration (order determines range resolution)
\tfgames{myproof}{G0, G1, Red1, G2}
\tfgamename{myproof}{G0}{G_0}
\tfgamename{myproof}{Red1}{\Bdversary_1}
\tfdescription{myproof}{G0}{The starting game.}
\tfreduction{myproof}{Red1}
\tfrelatedgames{myproof}{Red1}{G0, G1}

% Metadata for Python HTML export (no-ops in LaTeX)
\tfmacrofile{macros.tex}
\tfcommentary{myproof}{G0}{commentary/G0.tex}

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
\tfrendergame{myproof}{G0}                    % no highlighting
\tfrendergame[diff=G0]{myproof}{G1}           % changes from G0 highlighted
\tfrendergame{myproof}{G1}                    % clean, no highlighting
\tfrenderfigure{myproof}{G0,G1,G2}            % consolidated figure
```

> **Multiple proofs per document:** A single `.tex` file can define multiple independent
> proofs by using different source names. Each proof has its own `\tfgames`, `\tfgamename`,
> etc., all sharing the same source name, and its own `\begin{tfsource}{name}` block.

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

---

## Core Algorithms

### 1. Tag Range Resolution (`tex_parser.py: resolve_tag_ranges`)

Given `ordered_labels = ["G0","G1","G2","Red2","G3",...]` and `"G0,G3-G5"`:
- Split on `,`
- For tokens containing `-`: try splitting at each `-` to find two valid labels
- Resolve range to all labels between start and end (inclusive) by position
- Unknown single labels are kept verbatim (silently ignored at filter time)

### 2. Diff Computation (`filter.py: compute_changed_lines`)

Uses `difflib.SequenceMatcher` to align the previous game's filtered lines with the
current game's filtered lines. Returns a `set[int]` of 0-based indices into the
current lines that are insertions or replacements (not in the previous game).

The first game (index 0) always gets an empty changed set.

### 3. Change Highlighting (`filter.py: wrap_changed_line`)

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

## Segment Cropping (`\tfsegment`, `\tfcropdefault`, `crop=`)

For proofs with many hops, a diffed render can end up dominated by lines carried over unchanged from earlier games. `\tfsegment{Caption}` markers, placed at block depth 0 inside a `tfsource` body, divide the source into segments; a cropped render keeps only the segments that changed vs. the diff target (plus the always-kept first and last segment) and collapses each unchanged interior segment into its own `\tfsegmentstub{caption}` line (one stub per segment, each on its own line). The LaTeX package (`texfrog.sty`) and the Python HTML pipeline (`filter.py`/`output/html.py`) implement this independently, but with matching semantics (same keep-segment-0-and-final rule, same one-stub-per-segment output).

### LaTeX mechanism (`texfrog.sty`, `\__tf_render_game_cropped:nnn`)

Cropped rendering is a **3-pass process**, built on top of the existing diff-highlight machinery (`\g__tf_mode_int` dispatch: `0`=inactive, `1`=record, `2`=render, `3`=clean, `4`=figure; crop adds `5`=scan):

1. **Pass A --- record** (mode 1, identical to a non-cropped highlighted render): expand the source for the diff-*target* game into a discarded `\vbox`, recording which `\tfonly` position indices are active in that game (`\g__tf_recorded_prop`).
2. **Pass B --- scan** (mode 5, new): expand the source for the *current* game into a discarded `\vbox`. `\__tf_only_scan:nn` flags the enclosing segment as changed (`\g__tf_seg_changed_bool`) whenever a `\tfonly` block is active in the current game but wasn't recorded for the target (an add/change), or vice versa (a removal); it also *emits* the matching content into the discarded box, so the algpseudocodex line counter `ALG@line` steps for this game's numbered lines (untagged lines already execute in the scan). Each `\tfsegment` marker encountered during this pass (`\__tf_seg_boundary_scan:`) closes the current segment --- committing its changed flag into `\g__tf_active_seg_prop`, its ending `\tfonly` position into `\g__tf_seg_endpos_prop`, and (when `ALG@line` exists) the opening segment's absolute starting line number into `\g__tf_seg_startline_prop` --- and opens the next. The final segment (no trailing marker) is committed by hand once the pass finishes. Folding the line-number bookkeeping into this existing pass avoids a separate full-source expansion.
3. **Split**: the stored source token list is split at `\tfsegment{...}` markers (`\__tf_split_source_segments:n`, via `l3regex`) into per-segment token lists and captions, numbered identically to Pass B's segment count. This split operates on the **entire** stored source token list, so a marker must sit at its top brace level — nested inside a brace-group *argument* to another command (e.g. cryptocode's `\procedure{Name}{...}`, whose second argument is a literal `{...}` group), splitting there leaves each half brace-unbalanced and `\regex_split` fails with "Missing brace inserted" (no PDF). Line-based bodies (`\begin{algorithmic}...\end{algorithmic}`, `\begin{nicodemus}...\end{nicodemus}`, not wrapped in an extra box command) satisfy this naturally, since environments don't introduce a literal brace group around their content — **cropping is therefore effectively unsupported for cryptocode**; see `docs/writing-proofs.md`'s cropping section for the user-facing constraint.
4. **Pass C --- crop-render** (mode 2, the *same* highlighted-render mode used by non-cropped diffed renders): walk the segments in order (`\__tf_seg_render_one:n`). Segment 0 and the final segment always execute verbatim. Other segments execute verbatim if Pass B marked them active, or emit their own `\tfsegmentstub` line otherwise. Before each kept segment, `\__tf_seg_setline:n` restores absolute line numbering by `\setcounter{ALG@line}` to the value recorded in Pass B (a no-op for segment 0 and for profiles without the counter), so kept lines keep their full-listing numbers and the numbering **jumps** across a stub instead of renumbering contiguously. `\__tf_only_render:nn` --- the highlight logic --- is reused completely unchanged for whichever segments run.

A skipped segment never executes its `\tfonly` calls, so `\g__tf_pos_int` (the position counter Pass A/B use to align target and current games) would otherwise drift out of sync for later, *executed* segments. To prevent this, skipping a segment jumps `\g__tf_pos_int` forward to that segment's recorded ending position (`\g__tf_seg_endpos_prop`, captured in Pass B) before continuing, keeping highlight alignment correct for subsequent kept segments.

Dispatch: `\tfrendergame[diff=G, crop=on|off]{source}{game}` resolves an effective crop bool (`\__tf_resolve_crop_active:`) --- the `crop=` key wins if given; `crop=default` (the key's initial value) falls back to `\tfcropdefault`. Cropping is only ever consulted when `diff=` is present; a clean render (no `diff=`) always renders in full.

### Python HTML pipeline (`texfrog/filter.py`, `texfrog/output/html.py`)

The HTML build path mirrors the same semantics without any expl3 machinery, operating on plain filtered line lists:

- `split_into_segments(lines) -> list[Segment]` splits a game's filtered lines at `\tfsegment{caption}` marker lines (matched by `SEGMENT_RE`) into `Segment(caption, lines)` objects; content before the first marker becomes segment 0 with `caption=None`.
- `compute_active_segments(target_lines, curr_lines) -> set[int]` splits both the diff target's and the current game's lines into segments (they align 1:1, since the marker sequence is identical across games sharing one source) and returns the indices of current segments whose non-blank content differs from the aligned target segment.
- `crop_to_active_segments(lines, active, stub_macro=r"\tfsegmentstub", line_counter=None) -> tuple[list[str], list[int]]` rebuilds the line list keeping segment 0, the final segment, and every segment in `active` --- mirroring the LaTeX keep-0-and-final rule. Each skipped interior segment collapses to its own `{stub_macro}{{caption}}` line (one stub per segment, each on its own line; a blank/None caption yields an empty stub argument). When `line_counter` is set (`"ALG@line"` for `algpseudocodex`, from `PackageProfile.line_counter_name`), it inserts `\setcounter{<line_counter>}{N}` before each kept segment after segment 0 --- `N` being the number of numbered lines (`_count_numbered_lines`, matched by `_NUMBERED_LINE_RE`) in all preceding segments of the full input --- so the HTML output reproduces the LaTeX crop-render's absolute line numbers. Returns `(new_lines, idx_map)`, where `idx_map[k]` is the original line index of `new_lines[k]` (or `-1` for a synthesized stub or `\setcounter` line), so callers can remap other per-line data against the cropped output. The PDF uses the real `ALG@line` counter and is always exact; the HTML relies on `_NUMBERED_LINE_RE` matching algpseudocodex's default numbering (which numbers every statement/block command; the `noEnd` option, under which `\End...` lines are unnumbered, is not modeled).
- `_apply_crop` (`output/html.py`) is the call site: it combines `compute_active_segments` + `crop_to_active_segments` and remaps the `changed`-line index set through `idx_map`, so highlighting still lands on the correct (renumbered) lines in the cropped output.

`_apply_crop` is called from `generate_html`'s per-game loop **only when `proof.crop_default` is true** --- there is no per-game HTML override; the `crop=` key on `\tfrendergame` is consumed only by `texfrog.sty`, for the PDF path. `proof.crop_default` is parsed once per document (`tex_parser.py`, via `_extract_one_arg(text, "tfcropdefault")` over the whole file) and applies to every `Proof`/source block parsed from that file, matching the LaTeX side's single global `\g__tf_crop_default_bool`.

### Validation (`validate.py`)

`validate_proof` scans the raw source text for `\tfsegment{...}` markers plus a crude block-depth counter over `\If`/`\For`/`\While`/`\Function`/`\Procedure`/`\Loop`/`\Repeat` and their closers (`\ForAll` is counted once, via the `\For` opener prefix), warning on:

- a marker with an empty caption,
- a marker found at nonzero depth (inside an open block),
- `\tfcropdefault` on with zero `\tfsegment` markers in the source (nothing to crop), and
- a source line that contains `\tfsegment` but does not match `SEGMENT_RE` (a brace-containing caption, a marker sharing a line with other content, or a marker nested inside a `\tfonly{...}` body) — `SEGMENT_RE`'s `[^{}]*` caption charset (shared with the LaTeX-side scan regex) doesn't match any of these, so without this check they would otherwise silently misalign the split/crop machinery rather than surface a clear warning.

---

## LaTeX Output (in `output/html.py`)

### Per-game files: `{label}.tex`

Generated by `_write_game_file`. Contains filtered content with changed lines wrapped
in `\tfchanged{}`. **Blank/whitespace-only lines are skipped** — they arise from
excluded tagged content and cause `varwidth` dimension errors inside pseudocode
environments like cryptocode's `pcvstack`. **`\tfsegment{...}` marker lines are
also skipped** (matched via `filter.SEGMENT_RE`), regardless of whether cropping
is applied: `crop_to_active_segments` already removes markers from a *cropped*
game's lines, but an *uncropped* game (crop off, game 0 — `generate_html`'s
`i == 0` check always skips `_apply_crop` — or the `-clean`/`-removed`
variants, which never crop) would otherwise carry the marker through verbatim.
The HTML wrapper (`_build_wrapper_template`) doesn't load `texfrog.sty`, so an
unstripped marker there is an undefined control sequence — `pdflatex` still
emits a PDF under `-interaction=nonstopmode`, so the failure mode is a stray
caption line in the rendered SVG rather than a build error. The wrapper also
defines a no-op `\tfsegment` as defense in depth.

### Commentary files: `{label}_commentary.tex`

Generated only if commentary text is non-empty. Contains the content loaded from the
corresponding commentary file (e.g., `commentary/G0.tex` as specified in the proof `.tex` file).

---

## HTML Output (`output/html.py`)

### Pipeline

For each game:
1. Generate per-game `.tex` files (in a temp dir)
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
- **algpseudocodex** (text-mode content, like nicodemus): `\newcommand{\tfchanged}[1]{\highlightbox{#1}}`.
  The `\State` prefix is kept *outside* `\tfchanged{}`, exactly like nicodemus's `\item` — algorithmicx's
  `\State` does real vertical-mode box/`\prevdepth` bookkeeping that breaks if nested inside the highlight box.

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
    ├── Red1-G0-clean.svg    # clean panel for reduction Red1's related game G0
    ├── Red1-G1-clean.svg    # clean panel for reduction Red1's related game G1
    └── ...
```

Each game is compiled twice: once with `\tfchanged` highlighting (blue, for the
current-game panel) and once with `\tfremoved` highlighting (red strikethrough, for
the previous-game panel in side-by-side view showing lines that will be removed or
changed in the next game). The last game does not need a removed SVG since it never
appears as a "previous" game. A reduction's `related_games` panels get a third
"clean" compilation with no highlighting — one **per (reduction, related-game)
pair**, named `{reduction}-{related}-clean.svg`. When cropping is on, all panels of
a reduction (both related games *and* the reduction itself) are cropped to the same
segment set, so the flanking clean panels line up with the reduction rather than
showing a full listing (see below). A game related to two reductions therefore gets
two distinct clean files (different crops).

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

When `\tfcropdefault` is on, every panel of a reduction is cropped to a single shared
segment set (`_reduction_active_segments`): the union of the segments where any two of
the reduction's panels differ, plus the segments the reduction changes relative to its
diff target. All panels therefore keep the *same* segments and stub the rest, so the
reduction and its flanking related-game panels stay row-aligned. This set is generally
wider than the reduction's own diff-vs-target set — two related games can differ in a
segment the reduction leaves untouched (exactly the hop the reduction justifies), and
that segment must stay visible in all three panels rather than being cropped away or
shown only in a full, uncropped related-game listing.

### Live Reload (`watcher.py` + `output/html.py`)

By default, `html serve` watches the proof's source
files (input `.tex`, macros, preamble, commentary files) using `watchdog`
and automatically rebuilds + reloads the browser on changes.

**File watching** (`watcher.py`):
- `collect_watched_files(input_path)` discovers files to watch. For `.tex` input, it
  scans for `\tfmacrofile`, `\tfpreamble`, `\tfcommentary`, and `\input` commands.
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
texfrog init [DIRECTORY] [--package cryptocode|nicodemus|algpseudocodex]
texfrog check INPUT [--strict]
texfrog html build INPUT [-o DIR] [--keep-tmp]
texfrog html serve INPUT [-o DIR] [--port 8080] [--no-browser] [--no-live-reload]
```

INPUT can be a `.tex` file with TeXFrog commands or a directory containing `proof.tex`.

### `texfrog init`

Scaffolds a new proof directory with a `proof.tex` file containing TeXFrog commands,
a `macros.tex` file, a `commentary/` subdirectory with starter commentary files, and
a `.gitignore` covering LaTeX build artifacts and the default `texfrog html build` output.
The `--package` option selects the template flavour (default: `cryptocode`).
The `nicodemus` scaffold additionally bundles `nicodemus.sty` (copied from the
repository's `resources/` directory and registered via `\tfmacrofile{nicodemus.sty}`)
because that package is not on CTAN; this keeps the scaffold self-contained for both
`pdflatex` and `texfrog html build`. Existing files are never overwritten — skipped
with a warning instead.

Templates are stored as inline strings in `texfrog/templates.py` (non-CTAN `.sty`
resources live in `resources/`). Each template set produces a minimal 4-game proof
that is immediately compilable with `pdflatex`.

Default output dir: `texfrog_html/` next to the input file.

---

## Development Setup

```bash
cd TeXFrog/
python3 -m venv .venv
source .venv/bin/activate   # or: .venv/bin/activate.fish for fish shell
pip install -e ".[dev]"     # installs texfrog + pytest
texfrog --help
pytest tests/ -q            # 312 tests
```

System requirements (not pip-installable):
- `pdflatex` — from TeX Live / MacTeX
- `pdftocairo` — from poppler (via `brew install poppler` on macOS), OR `pdf2svg`
- `pdfcrop` — from TeX Live (optional but recommended for clean SVG cropping)

---

## Tutorials and Example Proofs

### `examples/tutorial-cryptocode-quickstart/` — IND-CPA (pure LaTeX format, preferred)

Implements a small IND-CPA proof (5 entries: G0, G1, Red1, G2, G3) using the pure LaTeX
format with `texfrog.sty`. The `.tex` file is the single source of truth — it compiles
directly with `pdflatex` and can also be used with `texfrog html build` for the HTML viewer.

### `examples/tutorial-cryptocode/` and `examples/tutorial-nicodemus/` — IND-CPA (pure LaTeX format)

Pure LaTeX format tutorials implementing the same small IND-CPA proof (4 entries: G0,
G1, Red1, G2). `tutorial-cryptocode/` uses `package=cryptocode` (default);
`tutorial-nicodemus/` uses `package=nicodemus`.

### `examples/tutorial-algpseudocodex/` — IND-CPA (pure LaTeX format, algpseudocodex)

Pure LaTeX format tutorial implementing the full 5-entry IND-CPA proof (G0, G1, Red1,
G2, G3), using `package=algpseudocodex`. Ported line-by-line from
`tutorial-nicodemus/`, demonstrating the `algorithmic`/`\Procedure`/`\State` syntax.

### `examples/example-multiproof/` — Multiple proofs in one document (pure LaTeX format, cryptocode)

Demonstrates defining multiple independent proofs in a single `.tex` file, each with
its own source name, games, and `tfsource` block.

---

## Package Profiles (`packages.py`)

Package-specific behavior is abstracted via `PackageProfile`:

| Attribute | cryptocode | nicodemus | algpseudocodex |
|-----------|-----------|-----------|-----------|
| `has_line_separators` | `True` (`\\` between lines) | `False` (`\item` per line) | `False` (`\State` per line) |
| `math_mode_content` | `True` (inside `\procedure`) | `False` (inside `\begin{nicodemus}`) | `False` (inside `\Procedure`) |
| `gamelabel_comment_cmd` | `\pccomment` | `None` | `\Comment` |
| `procedure_header_cmd` | `None` | `nicodemusheader` | `Procedure` |

Derived methods generate `\tfchanged`, `\tfremoved`, and `\tfgamelabel` definitions
appropriate for each package, used in both the LaTeX harness and HTML wrapper.

`.sty`/`.cls` files in the `macros:` list are handled specially: they are copied to
the build directory without renaming (so `\usepackage` can find them) and are NOT
`\input`'d in the harness.

---

## Known Limitations / Future Work
