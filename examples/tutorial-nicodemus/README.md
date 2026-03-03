# TeXFrog Tutorial (nicodemus)

> [!NOTE]
> **Package:** This tutorial uses [`nicodemus`](https://github.com/awslabs/nicodemus). For the same proof using `cryptocode` (the default, with a more detailed walkthrough), see [tutorial-cryptocode/](../tutorial-cryptocode/).

This tutorial contains the same IND-CPA proof as the cryptocode tutorial, rewritten for the `nicodemus` pseudocode package. Comparing the two shows the key syntax differences.

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
| `proof.yaml` | Declares the games, commentary, and figure specs (`package: nicodemus`) |
| `games_source.tex` | Combined LaTeX source with `%:tags:` annotations |
| `macros.tex` | Short macro definitions (no external dependencies) |
| `nicodemus.sty` | The nicodemus pseudocode package |

---

## Key Differences from the cryptocode Tutorial

The YAML configuration is almost identical. The main differences:

1. **`package: nicodemus`** is set at the top of the YAML.
2. **`nicodemus.sty`** is listed under `macros:` (`.sty` files are copied to the build directory for `\usepackage` but are not `\input`-ed).

The source file syntax differs substantially:

| cryptocode | nicodemus |
|-----------|-----------|
| `\begin{pcvstack}[boxed]` | `\begin{tabular}[t]{l}` + `\nicodemusboxNew{250pt}{%` |
| `\procedure[linenumbering]{Name}{` | `\nicodemusheader{Name}` |
| `k \getsr \{0,1\}^\lambda \\` | `\item $k \getsr \{0,1\}^\lambda$` |
| `\pcreturn (b' = b)` | `\item Return $(b' = b)$` |
| `}` (closing procedure) | `\end{nicodemus}%` |

**Key points:**
- **Text mode**: nicodemus environments are text-mode, so math content needs explicit `$...$`.
- **`\item` prefix**: Each pseudocode line starts with `\item` (nicodemus uses `enumerate`). The `\item` is kept outside `\tfchanged{}` to preserve list structure.
- **No `\\` separators**: List items are naturally separated.
- **`\nicodemusheader`**: Procedure headers use `\nicodemusheader{...}` above `\begin{nicodemus}` blocks. Like cryptocode's `\procedure{...}{` syntax, `\nicodemusheader` lines are never wrapped in `\tfchanged`.

---

## The Combined Source (`games_source.tex`)

### Lines with no tag appear in every game

```latex
\item $b \getsr \{0,1\}$
\item $b' \gets \Adversary^{\mathsf{LR}}()$
\item Return $(b' = b)$
```

### Lines with a tag appear only in named games

```latex
\item $k \getsr \{0,1\}^\lambda$ %:tags: G0
```

### Consecutive variant lines encode "slots"

The `y` computation is a four-way slot:

```latex
\item $y \gets \mathrm{PRF}(k, r)$ %:tags: G0
\item $y \gets \RF(r)$             %:tags: G1
\item $y \getsr \{0,1\}^\lambda$   %:tags: G2
\item $y \gets \OPRF(r)$           %:tags: Red1
```

For each game, at most one of these lines survives filtering. They are consecutive, so the chosen line always appears at the right position.

### Procedure headers

In nicodemus, procedure headers use `\nicodemusheader{...}` above `\begin{nicodemus}` environments:

```latex
\nicodemusheader{$\INDCPA_\Enc^\Adversary()$} %:tags: G0
\nicodemusheader{Game~$\tfgamename{G1}$} %:tags: G1
\nicodemusheader{Game~$\tfgamename{G2}$} %:tags: G2
\nicodemusheader{Game~$\tfgamename{G3}$} %:tags: G3
\nicodemusheader{Reduction $\Bdversary_1^{\OPRF}$} %:tags: Red1
```

---

## Running the Tutorial

From the repo root:

```bash
# Generate per-game LaTeX files
texfrog latex examples/tutorial-nicodemus/proof.yaml -o /tmp/tf_tutorial_nic_latex

# Build an interactive HTML viewer
texfrog html build examples/tutorial-nicodemus/proof.yaml -o /tmp/tf_tutorial_nic_html

# Or build and open in your browser with live reload
texfrog html serve examples/tutorial-nicodemus/proof.yaml --live-reload
```

---

## What `\tfchanged` Looks Like

The default highlight macro for nicodemus:

```latex
\providecommand{\tfchanged}[1]{\colorbox{blue!15}{#1}}
```

No `$...$` wrapping — unlike cryptocode, nicodemus content is text-mode. The `\item` prefix is kept outside `\tfchanged`:

```latex
\item \tfchanged{$y \getsr \{0,1\}^\lambda$}
```

---

## Next Steps

- [Writing a proof](../../docs/writing-proofs.md) — full reference for `proof.yaml` and source file syntax
- [tutorial-cryptocode/](../tutorial-cryptocode/) — the same proof using `cryptocode` (with a more detailed walkthrough)
- [LaTeX integration](../../docs/latex-integration.md) — customizing `\tfchanged` and `\tfgamelabel`
