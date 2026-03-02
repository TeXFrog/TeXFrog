# Using TeXFrog Output in Your LaTeX Paper

After running `texfrog latex`, you have a directory of generated files ready to include in your paper. This guide explains what each file does and how to use it.

## Generated Files

Running `texfrog latex proof.yaml -o output/` produces:

```
output/
├── proof_harness.tex       # main entry point — \input this in your paper
├── G0.tex                  # per-game pseudocode, one file per game
├── G1.tex
├── G0_commentary.tex       # per-game commentary (only if commentary was provided)
├── G1_commentary.tex
├── fig_start_end.tex       # consolidated figure (one per figures: entry)
└── ...
```

## The Quick Way: Use the Harness

The simplest way to include the full proof in your paper is to `\input` the harness:

```latex
\input{output/proof_harness.tex}
```

The harness automatically:
1. Defines the `\tfchanged`, `\tfgamelabel`, and `\tfgamename` macros (using `\providecommand`, so you can override them)
2. `\input`s your macro files
3. `\input`s each game file and its commentary, in order

### Harness Prerequisites

The harness uses `\colorbox`, which requires the `xcolor` package. Add to your preamble if not already present:

```latex
\usepackage{xcolor}
```

## Customizing the Highlight Macro

Changed lines are wrapped in `\tfchanged{content}`. The harness defines a default that depends on the package profile:

- **cryptocode**: `\providecommand{\tfchanged}[1]{\colorbox{blue!15}{$#1$}}`
- **nicodemus**: `\providecommand{\tfchanged}[1]{\colorbox{blue!15}{#1}}`

This renders changed lines with a light blue background. Because `\providecommand` is used, you can override it in your paper preamble simply by defining it yourself **before** `\input`-ing the harness:

```latex
% Use a yellow background instead:
\newcommand{\tfchanged}[1]{\colorbox{yellow!30}{$#1$}}

\input{output/proof_harness.tex}
```

Or suppress highlighting entirely (useful for the final paper version where you don't want colored boxes):

```latex
\newcommand{\tfchanged}[1]{#1}
\input{output/proof_harness.tex}
```

**Note on math mode:** For `cryptocode`, the default macro wraps content in `$...$` because the pseudocode content is in math mode and `\colorbox` operates in text mode. For `nicodemus`, content is already in text mode, so no `$...$` wrapping is needed. If you write a custom `\tfchanged`, match the mode of your pseudocode package.

## Customizing the Game Label Macro

In consolidated figures, lines that appear in only some of the selected games are annotated with `\tfgamelabel{labels}{content}`. The default depends on the package profile:

- **cryptocode**: `\providecommand{\tfgamelabel}[2]{#2 \pccomment{#1}}` — appends a `\pccomment` annotation
- **nicodemus**: `\providecommand{\tfgamelabel}[2]{#2}` — no annotation (nicodemus has no built-in comment macro)

Override before the harness to change the appearance:

```latex
% Use a margin note instead:
\newcommand{\tfgamelabel}[2]{#2\marginpar{\tiny #1}}
\input{output/proof_harness.tex}
```

## Referencing Game Names

TeXFrog generates a `\tfgamename{label}` macro that expands to the `latex_name` defined in your YAML config, wrapped in `\ensuremath`. Use it anywhere in your paper to reference a game by its label:

```latex
In \tfgamename{G1}, we replace the PRF call with a uniformly random value.
```

This works in both text mode and math mode:

```latex
% Text mode — \ensuremath enters math for you:
The advantage gap between \tfgamename{G0} and \tfgamename{G1} is bounded by \ldots

% Math mode — \ensuremath is a no-op:
$x = \tfgamename{G1}$
```

The macro is defined using `\providecommand`, so you can override it before `\input`-ing the harness. If you call `\tfgamename` with an undefined label, it silently produces no output.

In the HTML viewer, `\tfgamename{label}` in `description` fields is automatically expanded to `$latex_name$` for MathJax rendering. In commentary, `\tfgamename` is compiled natively by LaTeX (the HTML wrapper defines the macro), so no pre-expansion is needed.

## Including Individual Games

If you want finer control over where each game appears (e.g., interleaved with your own theorem and proof environments), include games individually instead of using the harness. Macro definitions need to come first:

```latex
% In your preamble:
\usepackage{xcolor}
\newcommand{\tfchanged}[1]{\colorbox{blue!15}{$#1$}}
\newcommand{\tfgamelabel}[2]{#2 \pccomment{#1}}
\input{output/proof_harness.tex}  % defines \tfgamename and \inputs macros
% Or define macros manually:
% \input{macros.tex}

% Then, where you want each game:
\input{output/G0.tex}

\begin{claim}
  Games~0 and~1 are indistinguishable \ldots
\end{claim}

\input{output/G1.tex}
\input{output/G1_commentary.tex}
```

## Consolidated Figures

Consolidated figures (generated from the `figures:` section in your YAML) show multiple games in a single view. Each line either appears verbatim (present in all selected games) or is annotated with game labels (present in only some).

Include a consolidated figure with:

```latex
\begin{figure}
\input{output/fig_start_end.tex}
\caption{Games G0 and G9 compared.}
\end{figure}
```

You will need to wrap the figure content in whatever pseudocode environment you use (`pcvstack`, `algorithmic`, etc.) — TeXFrog outputs only the body lines, not the surrounding environment. For example, with cryptocode:

```latex
\begin{figure}
\begin{pcvstack}[boxed]
\procedure{Comparison}{
\input{output/fig_start_end.tex}
}
\end{pcvstack}
\caption{Games G0 and G9.}
\end{figure}
```

## The HTML Viewer

Running `texfrog html build` or `texfrog html serve` produces a standalone HTML site — no integration with LaTeX required. The viewer:

- Shows each game as a rendered SVG, compiled via `pdflatex → pdfcrop → pdftocairo`
- Highlights changed lines with a colored box
- Displays game names (rendered with MathJax) and descriptions in the sidebar
- Supports keyboard navigation (left/right arrow keys) and URL hash links (`#G1`)
- Renders commentary as SVG images using the same LaTeX → PDF → SVG pipeline as game pseudocode

The HTML output is self-contained in its directory and can be served from any static file host, or opened directly in a browser.

**Commentary rendering:** Because commentary is compiled through LaTeX (not MathJax), any commands or environments used in commentary must be defined in your macros file. For example, if your commentary uses `\begin{claim}...\end{claim}`, your macros file must include `\newtheorem{claim}{Claim}`. The packages available in the HTML compilation wrapper include your selected pseudocode package plus `amsfonts`, `amsmath`, `amsthm`, `adjustbox`, and `xcolor`. Additional packages can be added via the `preamble` field in your YAML config.

### System Requirements for HTML

- `pdflatex` and your macro files (same TeX setup as your paper)
- `pdfcrop` (from TeX Live) — recommended for clean SVG margins
- `pdftocairo` (from poppler, `brew install poppler` on macOS) or `pdf2svg`

### Troubleshooting HTML Build

For a full list of common errors and solutions, see [Troubleshooting & FAQ](troubleshooting.md#html-build-issues).

**"Dimension too large" errors:** Do not use `\usepackage[active,tightpage]{preview}` in your macro files — it conflicts with `varwidth`, which is used internally by cryptocode's `pcvstack`. Similarly, do not use `\documentclass{standalone}`. (This is primarily a cryptocode issue.)

**Math mode errors in changed lines:** For `cryptocode`, the HTML wrapper defines `\tfchanged` using `\ensuremath{#1}` to handle math-mode content inside text-mode boxes. If you see errors like `\mathsf allowed only in math mode`, ensure your macro files do not redefine `\tfchanged` without `\ensuremath`. For `nicodemus`, content is text-mode so `\ensuremath` is not needed.

**Path errors:** If your project directory has spaces in its path, TeXFrog automatically copies files to a temporary directory before running pdflatex (since LaTeX's `\input{}` does not handle spaces). This is handled transparently.
