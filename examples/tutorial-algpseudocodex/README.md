# TeXFrog Tutorial (algpseudocodex)

> [!NOTE]
> **Package:** This tutorial uses [`algpseudocodex`](https://ctan.org/pkg/algpseudocodex). For the same proof using `cryptocode` (the default, with a more detailed walkthrough), see [tutorial-cryptocode/](../tutorial-cryptocode/).

This tutorial contains the same IND-CPA proof as the cryptocode tutorial, rewritten for the `algpseudocodex` pseudocode package. Comparing the two shows the key syntax differences.

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

`algpseudocodex.sty` is not vendored here — it ships as part of any full TeX Live / MacTeX installation. If `pdflatex` reports it missing, install it via your TeX distribution's package manager (e.g. `tlmgr install algpseudocodex`).

---

## Key Differences from the cryptocode Tutorial

The `.tex` file structure is the same (game registration, `tfsource` environment, rendering commands). The main differences are in the pseudocode syntax:

1. **`\usepackage[package=algpseudocodex]{texfrog}`** selects the algpseudocodex package profile.
2. **No macro-file entry for the package itself** — unlike `nicodemus.sty` (a project resource copied into the build directory), `algpseudocodex.sty` is a system package resolved by `pdflatex` directly, so it is not listed via `\tfmacrofile`.

The source syntax differs substantially:

| cryptocode | algpseudocodex |
|-----------|-----------|
| `\begin{pcvstack}[boxed]` | `\begin{algorithmic}[1]` |
| `\procedure[linenumbering]{Name}{` | `\Procedure{Name}{}` |
| `k \getsr \{0,1\}^\lambda \\` | `\State $k \getsr \{0,1\}^\lambda$` |
| `\pcreturn (b' = b)` | `\State \Return $(b' = b)$` |
| `}` (closing procedure) | `\EndProcedure` |

**Key points:**
- **Text mode**: algpseudocodex environments are text-mode, so math content needs explicit `$...$`.
- **`\State` per line**: Each pseudocode line is its own `\State` (no `\\` separators between lines, unlike cryptocode).
- **`\Procedure`**: Procedure headers use `\Procedure{...}{}` ... `\EndProcedure`. Like cryptocode's `\procedure{...}{` syntax, `\Procedure{...}` lines are never wrapped in `\tfchanged`.
- **`\Comment`**: algpseudocodex's built-in inline-comment macro is reused for the small game-label annotations shown in consolidated figures.

---

## The Proof Source (`main.tex`)

### Lines with no tag appear in every game

```latex
\State $b \getsr \{0,1\}$
\State $b' \gets \Adversary^{\mathsf{LR}}()$
\State \Return $(b' = b)$
```

### Lines with a tag appear only in named games

```latex
\tfonly{G0,G1-G3}{\State $k \getsr \{0,1\}^\lambda$}
```

### Consecutive variant lines encode "slots"

The `y` computation is a four-way slot:

```latex
\tfonly{G0}{\State $y \gets \mathrm{PRF}(k, r)$}
\tfonly{G1}{\State $y \gets \RF(r)$}
\tfonly{G2}{\State $y \getsr \{0,1\}^\lambda$}
\tfonly{Red1}{\State $y \gets \OPRF(r)$}
```

For each game, at most one of these lines survives filtering. They are consecutive, so the chosen line always appears at the right position.

### Procedure headers

In algpseudocodex, procedure headers use `\Procedure{...}{}` above the procedure body. Since the header text itself varies per game, the `\tfonly`-tagged alternatives are concatenated as the single `\Procedure`'s title argument (only one survives per-game filtering) rather than duplicating the whole `\Procedure`/`\EndProcedure` pair per game:

```latex
\Procedure{%
  \tfonly*{G0}{$\INDCPA_\Enc^\Adversary()$}%
  \tfonly*{G1}{Game~$\tfgamename{G1}$}%
}{}
```

---

## Running the Tutorial

### Compiling with pdflatex (no Python needed)

The `.tex` file compiles directly with `pdflatex`. You need `texfrog.sty` in the same directory, and `algpseudocodex.sty` available in your TeX distribution:

```bash
cd examples/tutorial-algpseudocodex
pdflatex main.tex
```

This also works on Overleaf (which includes `algpseudocodex` by default) — upload `texfrog.sty`, `main.tex`, `macros.tex`, and the `commentary/` files to a project and compile.

### Building the HTML viewer (requires Python CLI)

If you have the Python CLI installed, you can also build an interactive HTML viewer:

```bash
# Build an interactive HTML viewer
texfrog html build examples/tutorial-algpseudocodex/main.tex -o /tmp/tf_tutorial_alg_html

# Or build and open in your browser with live reload
texfrog html serve examples/tutorial-algpseudocodex/main.tex
```

---

## What `\tfchanged` Looks Like

The default highlight macro for algpseudocodex:

```latex
\providecommand{\tfchanged}[1]{\colorbox{blue!15}{#1}}
```

No `$...$` wrapping — unlike cryptocode, algpseudocodex content is text-mode.

---

## Next Steps

- [Writing a proof](../../docs/writing-proofs.md) — full reference for the `.tex` input format
- [tutorial-cryptocode/](../tutorial-cryptocode/) — the same proof using `cryptocode` (with a more detailed walkthrough)
