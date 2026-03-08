# Writing a Proof

This is the reference guide for TeXFrog's `.tex` input format. For a hands-on introduction, start with the [cryptocode quickstart](../examples/tutorial-cryptocode-quickstart/), the [cryptocode tutorial](../examples/tutorial-cryptocode/), or the [nicodemus tutorial](../examples/tutorial-nicodemus/) instead.

> [!TIP]
> Run `texfrog init` to scaffold a starter proof with commented templates, then modify the generated files. Use `texfrog init --package nicodemus` for nicodemus-flavored templates.

## Overview

A game-hopping proof consists of a sequence of games (and reductions) where adjacent games usually differ by only a few lines of pseudocode. TeXFrog lets you write all games in a single source block, using `\tfonly{tags}{content}` to control which content appears in which game. Lines not wrapped in `\tfonly` appear in every game.

## The .tex Input File

The `.tex` file is the **single source of truth**. It serves two purposes:

1. **Direct LaTeX compilation** via `pdflatex` using the `texfrog.sty` package, which handles game filtering, automatic diff highlighting, and consolidated figures entirely at compile time. This works standalone — you only need `texfrog.sty` in your project directory (or on Overleaf), with no Python installation required.
2. **HTML export** (optional) via the Python CLI tool (`texfrog html build`), which parses the same `.tex` file and builds an interactive HTML site with side-by-side game comparison, commentary, and MathJax rendering.

A minimal `.tex` file looks like this:

```latex
\documentclass{article}
\usepackage[package=cryptocode]{texfrog}

\input{macros.tex}

\tfgames{G0, G1, Red1, G2}
\tfgamename{G0}{G_0}
\tfgamename{G1}{G_1}
\tfgamename{Red1}{\Bdversary_1}
\tfgamename{G2}{G_2}

\tfdescription{G0}{The starting game.}
\tfdescription{G1}{Replace PRF with random function.}
\tfdescription{Red1}{Reduction to PRF security.}
\tfdescription{G2}{Replace random function output with uniform randomness.}

\tfreduction{Red1}
\tfrelatedgames{Red1}{G0, G1}

\tfmacrofile{macros.tex}

\begin{tfsource}{myproof}
  % ... pseudocode with \tfonly tags ...
\end{tfsource}

\begin{document}
\tfrendergame{myproof}{G0}
\tfrendergame{myproof}{G1}
\tfrenderfigure{myproof}{G0,G1,G2}
\end{document}
```

### Package Selection

Select the pseudocode LaTeX package with the `package` option on `\usepackage`:

```latex
\usepackage[package=cryptocode]{texfrog}   % default
\usepackage[package=nicodemus]{texfrog}
```

This controls how TeXFrog generates macro definitions (e.g., whether `\tfchanged` wraps content in math mode), how it handles line separators in consolidated figures, and which packages are loaded in the HTML build wrapper. If the `package` option is omitted, it defaults to `cryptocode`.

### Game Registration

Register the games and reductions in your proof using the following commands. These must appear in the preamble (before `\begin{document}`).

**`\tfgames{G0, G1, Red1, G2}`** declares the ordered list of all games and reductions. The order here is the canonical sequence of the proof --- it determines which games are "adjacent" for diff highlighting, and it defines what tag ranges like `G0-G2` mean.

**`\tfgamename{label}{latex_name}`** sets the display name for a game. The `latex_name` is math-mode content without `$` delimiters (e.g., `G_0` or `\indcca_\QSH^\adv.\REAL()`). It is rendered via `\ensuremath` in LaTeX and `$...$` in the HTML viewer.

```latex
\tfgamename{G0}{G_0}
\tfgamename{Red1}{\Bdversary_1}
```

**`\tfdescription{label}{text}`** sets a one-sentence LaTeX description shown in the HTML viewer sidebar.

```latex
\tfdescription{G0}{The starting game (real IND-CCA game).}
\tfdescription{G1}{Replace $\key_2$ with a fresh $\key_2^*$ from encapsulation.}
```

**`\tfreduction{label}`** marks a game as a reduction. In the HTML viewer, reductions are displayed alone rather than side-by-side with the previous game (unless `\tfrelatedgames` is set).

**`\tfrelatedgames{label}{G0, G1}`** specifies zero, one, or two game labels to display alongside a reduction in the HTML viewer. Only valid for games marked with `\tfreduction`. Clean (unhighlighted) versions of these games are shown next to the reduction: one related game gives a 2-panel layout, two gives a 3-panel layout with the reduction in the middle.

```latex
\tfreduction{Red2}
\tfrelatedgames{Red2}{G1, G2}
```

Labels can be anything: `G0`, `Red2`, `Hybrid3`, `BadEvent` --- TeXFrog treats them as arbitrary strings.

### Macros and Preamble

> [!NOTE]
> The `\tfmacrofile`, `\tfpreamble`, `\tfcommentary`, and `\tffigure` commands are metadata for the Python CLI's HTML export. They are silently ignored during normal `pdflatex` compilation, so they are harmless to include even if you only use the LaTeX package.

**`\tfmacrofile{macros.tex}`** declares a macro file (relative to the `.tex` file's location) that should be included in the HTML build. You can use multiple `\tfmacrofile` commands. `.tex` files are `\input`-ed into the HTML compilation. `.sty` and `.cls` files are copied to the build directory (so `\usepackage` can find them) but are NOT `\input`-ed.

```latex
\tfmacrofile{macros.tex}
\tfmacrofile{../shared/crypto-macros.tex}
\tfmacrofile{nicodemus.sty}
```

**`\tfpreamble{preamble.tex}`** declares a file containing extra `\usepackage` lines needed for the HTML build, relative to the `.tex` file. Use this for packages that your proof needs beyond what the package profile provides. For example, if your macros use `\usepackage{stmaryrd}` or `\usepackage{lmodern}`, list them in the preamble file.

```latex
\tfpreamble{preamble.tex}
```

### Commentary

**`\tfcommentary{label}{commentary/G0.tex}`** associates per-game commentary with a game. The value is a path (relative to the `.tex` file) to a `.tex` file containing free-form LaTeX. Commentary is rendered in the HTML viewer below the game pseudocode.

```latex
\tfcommentary{G0}{commentary/G0.tex}
\tfcommentary{G1}{commentary/G1.tex}
```

Each commentary file contains raw LaTeX --- environments, math, and display equations all work. For example, `commentary/G1.tex` might contain:

```latex
\begin{claim}
  Games~0 and~1 are indistinguishable assuming correctness of $\KEM_2$.
\end{claim}
This follows by inlining the decapsulation result.
```

You can use `\tfgamename{G1}` in commentary to reference a game's `latex_name`.

**HTML viewer:** Commentary is compiled through the same LaTeX -> PDF -> SVG pipeline as game pseudocode, so any LaTeX commands or environments used in commentary (e.g., `\newtheorem{claim}{Claim}`) must be defined in your macros file. The packages available in the HTML compilation wrapper include your selected pseudocode package (e.g., `cryptocode` or `nicodemus`), plus `amsfonts`, `amsmath`, `amsthm`, `adjustbox`, and `xcolor`. Additional packages can be added via `\tfpreamble`.

### Figures

**`\tffigure[procedure_name]{label}{games}`** declares a consolidated figure showing multiple games side by side, for use as a comparison table in your paper. The Python HTML tool uses this metadata; `texfrog.sty` provides `\tfrenderfigure` for the LaTeX side.

```latex
\tffigure{start_end}{G0,G9}
\tffigure[Games $G_0$--$G_9$]{main_proof}{G0-G2,G8,G9}
```

Each figure has:
- `label` --- used as the output filename: `fig_{label}.tex`
- `games` --- comma-separated list or range of game labels (same syntax as `\tfonly` tags)
- `procedure_name` (optional) --- custom title for the first procedure header in the consolidated output. Without this, the first game's header is used verbatim. Useful for showing a collective name like "Games $G_0$--$G_9$" instead of a single game's title.

In the generated figure, lines that appear in all selected games are output verbatim. Lines that appear in only some games are annotated with `\tfgamelabel{G1,G3}{line content}`.

### Proof Source

The `tfsource` environment contains the pseudocode for all games merged together.

**`\begin{tfsource}{name}...\end{tfsource}`** defines a named source block. The `name` is referenced by `\tfrendergame` and `\tfrenderfigure`.

```latex
\begin{tfsource}{indcpa}
\begin{pcvstack}[boxed]
  \procedure[linenumbering]{%
    \tfonly*{G0}{Game $\tfgamename{G0}$}%
    \tfonly*{G1}{Game $\tfgamename{G1}$}%
    \tffigonly{Games $\tfgamename{G0}$--$\tfgamename{G1}$}%
  }{
    \tfonly{G0}{k \getsr \{0,1\}^\lambda \\}
    b \getsr \{0,1\} \\
    b' \gets \Adversary^{\mathsf{LR}}() \\
    \pcreturn (b' = b)
  }
\end{pcvstack}
\end{tfsource}
```

Inside `tfsource`, use the following commands to control which content appears in which games:

**`\tfonly{tags}{content}`** --- content appears only in the listed games. Lines not wrapped in `\tfonly` appear in every game.

```latex
\tfonly{G0}{k \getsr \{0,1\}^\lambda \\}
\tfonly{G1}{y \gets \RF(r) \\}
\tfonly{G2}{y \getsr \{0,1\}^\lambda \\}
```

**`\tfonly*{tags}{content}`** --- like `\tfonly` but suppressed in consolidated figures (`\tfrenderfigure`). Use for per-game procedure headers that should not appear in the combined view.

**`\tffigonly{content}`** --- shown only in consolidated figures, hidden in single-game rendering. Use for a combined header in `\tfrenderfigure` output.

Typical pattern for procedure headers:

```latex
\procedure[linenumbering]{%
  \tfonly*{G0}{Game $\tfgamename{G0}$}%
  \tfonly*{G1}{Game $\tfgamename{G1}$}%
  \tffigonly{Games $\tfgamename{G0}$--$\tfgamename{G1}$}%
}{...}
```

### Tag Syntax

The `tags` argument in `\tfonly{tags}{content}` specifies which games should include the content:

- **Single label**: `\tfonly{G0}{content}`
- **Comma-separated list**: `\tfonly{G0,G3,Red2}{content}`
- **Range**: `\tfonly{G0-G9}{content}` --- includes all games from G0 to G9 *by position in the games list*
- **Mixed**: `\tfonly{G0,G3-G5}{content}`

### Range Resolution

Ranges are resolved **positionally** --- by the order games appear in the `\tfgames` declaration, not alphabetically or numerically. Given the game list `\tfgames{G0, G1, G2, Red2, G3, G4}`, the tag `G1-G3` includes `G1`, `G2`, `Red2`, and `G3`, because `Red2` sits between `G2` and `G3` in the sequence.

This lets you insert reductions (e.g., `Red2`) between games without breaking range syntax.

Unknown labels in tags will raise a warning on the command line but otherwise are silently ignored, so a typo like `G10` when `G10` doesn't exist will simply cause the content to appear in no game. Run `texfrog check --strict` to catch these --- see [Troubleshooting](troubleshooting.md#lines-are-missing-from-a-game).

### Source Ordering Constraint

**This is the most important constraint in TeXFrog.**

Variant content for the same logical "slot" --- alternatives of each other in different games --- must be **consecutive** in the source. TeXFrog filters content but does not reorder it.

For example, the KEM_2 encaps line varies across games:

```latex
% Correct: variants are consecutive
\tfonly{G0}{(\ct_2^*, \key_2) \getsr \KEM_2.\encaps(\pk_2) \\}
\tfonly{G1}{(\ct_2^*, \key_2^*) \getsr \KEM_2.\encaps(\pk_2) \\}
\tfonly{G2-G9}{(\ct_2^*, \_\_) \getsr \KEM_2.\encaps(\pk_2) \\}
```

If you placed these in different parts of the source, they would all appear together at the wrong point in the filtered output. Keep variants for the same slot consecutive.

### Rendering

Use these commands in the document body to render games and figures.

**`\tfrendergame{source}{label}`** renders a single game. The first game in the sequence has no diff highlighting; subsequent games automatically highlight changes relative to the previous game.

**`\tfrendergame[highlight=false]{source}{label}`** renders a game without diff highlighting ("clean" version).

**`\tfrenderfigure{source}{games}`** renders a consolidated figure showing multiple games side by side.

```latex
\tfrendergame{indcpa}{G0}                     % no highlighting (first game)
\tfrendergame{indcpa}{G1}                     % auto-highlighted changes
\tfrendergame[highlight=false]{indcpa}{G1}    % clean, no highlighting
\tfrenderfigure{indcpa}{G0,G1,G2,G3}          % consolidated figure
```

### Lines That Are Not Wrapped in `\tfchanged`

When generating the LaTeX output, TeXFrog wraps changed lines in `\tfchanged{}` to highlight them. Two kinds of lines are never wrapped, even if they changed:

- **Procedure headers**: lines ending with `{` (e.g., `\procedure{Name}{`). Wrapping these would break LaTeX brace matching.
- **Pure comment lines**: lines that start with `%`. These are invisible in the PDF, so wrapping them is pointless.

### Tips for Writing the Source

**Structure your source top-to-bottom** in the same order the pseudocode will appear in the rendered games. The `tfsource` block is essentially the pseudocode of any single game, with variant content for other games interleaved via `\tfonly`.

**Use comments to label sections.** The source block is read by both you and TeXFrog. Comments like `%%% --- Oracle section ---` help orient readers and are harmless (comment lines are never wrapped).

**One game header per game.** If you use `\procedure` environments, put each game's procedure header as a `\tfonly*` call so only the right header appears in each game:

```latex
\procedure[linenumbering]{%
  \tfonly*{G0}{Starting game $= \indcca_\QSH^\adv.\REAL()$}%
  \tfonly*{G1}{Game~1}%
  \tfonly*{G2}{Game~2}%
  \tffigonly{Games $G_0$--$G_2$}%
}{...}
```

**Avoid blank lines in the source block.** Blank lines in output are stripped to prevent `varwidth` dimension errors in pseudocode environments like `pcvstack`. See [Troubleshooting](troubleshooting.md#dimension-too-large-from-pdflatex) for more on this error.

## Package-Specific Notes

### cryptocode (default)

- Lines end with `\\` as a separator (except the last line of each procedure body)
- Content is in math mode (inside `\procedure` environments)
- `\tfchanged` wraps content in `$...$` for text-mode containers
- Consolidated figures insert `\\` between adjacent game-specific lines
- `\tfgamelabel` uses `\pccomment` for inline game labels

### nicodemus

- Lines start with `\item` (enumerate-based pseudocode)
- Content is in text mode (inside `\begin{nicodemus}` environments)
- `\tfchanged` wraps content directly (no math-mode wrapping)
- `\item` prefix is kept outside `\tfchanged{}` to preserve list structure
- Consolidated figures do NOT insert `\\` between lines
- `\tfgamelabel` outputs the content without a comment macro

## Examples

The repository includes worked examples you can study and run. All examples compile directly with `pdflatex` (no Python needed) — just place `texfrog.sty` in the same directory.

- [tutorial-cryptocode-quickstart/](../examples/tutorial-cryptocode-quickstart/) --- IND-CPA proof using the pure LaTeX format with `texfrog.sty` (recommended starting point, especially if you are not using the Python CLI)
- [tutorial-cryptocode/](../examples/tutorial-cryptocode/) --- IND-CPA proof using `cryptocode` with a detailed walkthrough and commentary files
- [tutorial-nicodemus/](../examples/tutorial-nicodemus/) --- same proof using `nicodemus`, showing the syntax differences
- [example-compositekems/](../examples/example-compositekems/) --- larger QSH IND-CCA proof with 12 games/reductions
- [example-ntor/](../examples/example-ntor/) --- ntor key exchange proof
