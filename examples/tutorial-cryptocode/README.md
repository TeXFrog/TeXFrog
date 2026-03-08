# TeXFrog Tutorial (cryptocode)

> [!NOTE]
> **Package:** This tutorial uses [`cryptocode`](https://ctan.org/pkg/cryptocode) (the default). For the same proof using `nicodemus`, see [tutorial-nicodemus/](../tutorial-nicodemus/).

This tutorial walks through a small, complete game-hopping proof to introduce important TeXFrog concepts. The proof is short enough to read in full, but exercises several features of the tool.

## The Proof Scenario

**Scheme.** A symmetric encryption scheme:

```
Enc(k, m)  =  (r, PRF(k, r) XOR m)    where r is fresh per call
Dec(k, (r, c))  =  PRF(k, r) XOR c
```

**Theorem.** `Enc` is IND-CPA secure if `PRF` is a secure pseudorandom function.

**Proof.** Via a three-hop game sequence:

```
G0 (Real)  ~_PRF  G1  ~_birthday  G2  =  G3 (Ideal)
```

| Game | What changes |
|------|-------------|
| G0 | Oracle computes `y <- PRF(k, r)`, returns `(r, y XOR m_b)` |
| G1 | Oracle computes `y <- RF(r)` (truly random function), returns `(r, y XOR m_b)` |
| G2 | Oracle samples `y` at random, returns `(r, y XOR m_b)` |
| G3 | Oracle samples `c` directly (message not used) |
| Red1 | Reduction: replaces PRF call by querying an external challenger |

G0 to G1 is by PRF security (via Red1). G1 to G2 is by a birthday bound on nonce collisions. G2 to G3 is a perfect equivalence.

## Files in This Directory

| File | Purpose |
|------|---------|
| `main.tex` | Single source file: declares games, contains pseudocode with `\tfonly` tags, and renders output |
| `macros.tex` | Short macro definitions (no external dependencies) |
| `commentary/*.tex` | Per-game commentary files (LaTeX) |

---

## Step 1 — The Source File (`main.tex`)

The `.tex` file is the single source of truth. It compiles directly with `pdflatex` (using `texfrog.sty`) and is also parsed by the Python CLI tool for HTML export.

### Package and game registration

```latex
\usepackage[package=cryptocode]{texfrog}

\tfgames{indcpa}{G0, G1, Red1, G2, G3}
\tfgamename{indcpa}{G0}{G_0}
\tfgamename{indcpa}{Red1}{\Bdversary_1}
\tfdescription{indcpa}{G0}{The IND-CPA game. The LR oracle encrypts using the actual PRF.}
\tfreduction{indcpa}{Red1}
\tfrelatedgames{indcpa}{Red1}{G0, G1}
```

`\tfgames` declares the ordered list of all games and reductions. The order matters for diffing and range resolution. `\tfgamename` sets the display name (math-mode content without `$` delimiters). `\tfreduction` marks an entry as a reduction.

### Metadata for HTML export

```latex
\tfmacrofile{macros.tex}
\tfcommentary{indcpa}{G0}{commentary/G0.tex}
```

`\tfmacrofile` declares files needed in the HTML build. `\tfcommentary` associates per-game commentary.

### The proof source

```latex
\begin{tfsource}{indcpa}
\begin{pcvstack}[boxed]
  \procedure[linenumbering]{%
    \tfonly*{G0}{Game $\tfgamename{G0}$}%
    \tfonly*{G1}{Game $\tfgamename{G1}$}%
    ...
  }{
    \tfonly{G0,G1-G3}{k \getsr \{0,1\}^\lambda \\}
    ...
    \tfonly{G0}{y \gets \mathrm{PRF}(k, r) \\}
    \tfonly{G1}{y \gets \RF(r) \\}
    \tfonly{G2}{y \getsr \{0,1\}^\lambda \\}
    \tfonly{Red1}{y \gets \OPRF(r) \\}
    ...
  }
\end{pcvstack}
\end{tfsource}
```

All pseudocode lives in a single `tfsource` environment. Lines not wrapped in `\tfonly` appear in every game. Lines inside `\tfonly{tags}{content}` appear only in the listed games.

### Lines with no tag appear in every game

```latex
b \getsr \{0,1\} \\
b' \gets \Adversary^{\mathsf{LR}}() \\
\pcreturn (b' = b)
```

These lines are identical across G0, G1, G2, G3, and Red1.

### Lines with a tag appear only in named games

```latex
\tfonly{G0,G1-G3}{k \getsr \{0,1\}^\lambda \\}
```

The tag `G0,G1-G3` includes G0 (position 0) plus positions from G1 to G3 (positions 2–4): G1, G2, G3. Red1 (position 1) does not get this line.

### Consecutive variant lines encode "slots"

**This is the most important structural rule:** variant lines for the same logical slot must be consecutive in the source file. TeXFrog filters but never reorders lines.

The `y` computation is a four-way slot:

```latex
\tfonly{G0}{y \gets \mathrm{PRF}(k, r) \\}
\tfonly{G1}{y \gets \RF(r) \\}
\tfonly{G2}{y \getsr \{0,1\}^\lambda \\}
\tfonly{Red1}{y \gets \OPRF(r) \\}
```

For each game, at most one of these lines survives filtering. They are consecutive, so the chosen line always appears at the right position.

### Procedure headers

Procedure headers use `\tfonly*` (starred) so they appear in individual games but are suppressed in consolidated figures:

```latex
\procedure[linenumbering]{%
  \tfonly*{G0}{Game $\tfgamename{G0}$}%
  \tfonly*{G1}{Game $\tfgamename{G1}$}%
  \tffigonly{Games $\tfgamename{G0}$--$\tfgamename{G3}$}%
}{...}
```

### Rendering

```latex
\tfrendergame{indcpa}{G0}                    % no highlighting
\tfrendergame[diff=G0]{indcpa}{G1}           % changes from G0 highlighted
\tfrenderfigure{indcpa}{G0,G1,G2,G3,Red1}   % consolidated figure
```

---

## Step 2 — Running the Tutorial

### Compiling with pdflatex (no Python needed)

The `.tex` file compiles directly with `pdflatex`. You just need `texfrog.sty` in the same directory (or installed where TeX can find it):

```bash
cd examples/tutorial-cryptocode
pdflatex main.tex
```

This also works on Overleaf — upload `texfrog.sty`, `main.tex`, `macros.tex`, and the `commentary/` files to a project and compile.

### Building the HTML viewer (requires Python CLI)

If you have the Python CLI installed, you can also build an interactive HTML viewer:

```bash
# Build an interactive HTML viewer
texfrog html build examples/tutorial-cryptocode/main.tex -o /tmp/tf_tutorial_html

# Or build and open in your browser with live reload
texfrog html serve examples/tutorial-cryptocode/main.tex
```

---

## Key Concepts Summary

| Concept | Where demonstrated |
|---------|-------------------|
| Untagged lines appear in every game | `b`, `b'`, `\pcreturn` lines |
| Single-game tag | `\tfonly{G0}{...}`, `\tfonly{G3}{...}` |
| Comma-separated tag list | `\tfonly{G0,G1-G3}{...}` |
| Range tag | `G0-G2` (positions 0–3, covers G0, Red1, G1, G2) |
| Consecutive variant slot | The four `y` lines; the two `c` lines |
| Changed-line highlighting | `y` highlighted in G1; `c` highlighted in G3 |
| Consolidated figure | `\tfrenderfigure` annotates game-specific lines |
| `\tfgamename` | Commentary uses `\tfgamename{G0}` to reference game names |

---

## Next Steps

- [Writing a proof](../../docs/writing-proofs.md) — full reference for the `.tex` input format
- [tutorial-nicodemus/](../tutorial-nicodemus/) — the same proof using the `nicodemus` package
