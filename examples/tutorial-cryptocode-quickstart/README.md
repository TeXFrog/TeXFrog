# TeXFrog Tutorial (Cryptocode Quickstart)

> [!NOTE]
> **No Python required.** This tutorial uses only `texfrog.sty` and compiles directly with `pdflatex`. It is the recommended starting point for anyone who wants to try TeXFrog without installing the Python CLI.

This tutorial contains a small, complete IND-CPA game-hopping proof that demonstrates the core features of TeXFrog: game filtering with `\tfonly`, automatic diff highlighting, and consolidated comparison figures.

For more detailed explanations of each concept, see the [cryptocode tutorial](../tutorial-cryptocode/) (same proof, with a longer walkthrough). For the same proof using the `nicodemus` pseudocode package, see the [nicodemus tutorial](../tutorial-nicodemus/).

## Files in This Directory

| File | Purpose |
|------|---------|
| `main.tex` | Complete proof: game declarations, pseudocode source, and rendered output |
| `macros.tex` | Short macro definitions |

You also need `texfrog.sty` from the [latex/](../../latex/) directory of the repository.

## Getting Started

### On your computer

1. Copy `main.tex`, `macros.tex`, and `texfrog.sty` into the same directory.
2. Compile with `pdflatex main.tex`.
3. Open `main.pdf` to see the rendered games with diff highlighting.

### On Overleaf

1. Create a new blank project on Overleaf.
2. Upload `main.tex`, `macros.tex`, and `texfrog.sty`.
3. Compile. The PDF shows each game individually (with changes highlighted) and a consolidated comparison figure.

## What to Look For in the Output

- **Game G0** renders with no highlighting (it is the first game in the sequence).
- **Game G1** highlights the line that changed from G0 (the PRF is replaced by a random function).
- **Game G1 (clean)** renders G1 without highlighting, using `\tfrendergame[highlight=false]`.
- **Game G2** highlights the line that changed from G1.
- **Reduction Red1** highlights the line that changed from G1 (the previous non-reduction game).
- **Game G3** highlights the line that changed from G2.
- **Consolidated figure** shows G0, G1, G2, and G3 side by side, with game-specific lines annotated.

## How the Source Works

All pseudocode lives in a single `\begin{tfsource}{indcpa}...\end{tfsource}` block. Lines not wrapped in `\tfonly` appear in every game. Lines inside `\tfonly{tags}{content}` appear only in the listed games.

```latex
% This line appears in every game:
b \getsr \{0,1\} \\

% These are alternatives — only one appears per game:
\tfonly{G0}{y \gets \mathrm{PRF}(k, r) \\}
\tfonly{G1}{y \gets \RF(r) \\}
\tfonly{G2}{y \getsr \{0,1\}^\lambda \\}
\tfonly{Red1}{y \gets \OPRF(r) \\}
```

Rendering is done with `\tfrendergame` (single game) and `\tfrenderfigure` (consolidated figure):

```latex
\tfrendergame{indcpa}{G0}                    % no highlighting (first game)
\tfrendergame{indcpa}{G1}                    % changes from G0 highlighted
\tfrenderfigure{indcpa}{G0,G1,G2,G3}        % side-by-side comparison
```

## Customizing the Highlight Style

The default highlight is a light blue background. To change it, redefine `\tfchanged` in your preamble:

```latex
% Red underline instead of blue background
\renewcommand{\tfchanged}[1]{\underline{\textcolor{red}{#1}}}

% No highlighting at all (useful for camera-ready versions)
\renewcommand{\tfchanged}[1]{#1}
```

## Next Steps

- Modify `main.tex` to add a new game or change lines, then recompile to see how highlighting updates automatically.
- [Writing a proof](../../docs/writing-proofs.md) --- full reference for the `.tex` input format.
- [tutorial-cryptocode/](../tutorial-cryptocode/) --- the same proof with a more detailed walkthrough and commentary files.
- If you install the Python CLI, you can also run `texfrog html serve main.tex --live-reload` to get an interactive HTML proof viewer.
