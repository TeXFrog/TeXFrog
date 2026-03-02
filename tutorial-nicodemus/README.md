# TeXFrog Tutorial (nicodemus)

> **Note:** This tutorial uses the `nicodemus` package. For the same proof using `cryptocode` (the default), see [tutorial-cryptocode/](../tutorial-cryptocode/).

This tutorial contains the same IND-CPA proof as the `tutorial-cryptocode/` directory, rewritten
for the `nicodemus` pseudocode package. Comparing the two shows the key syntax differences.

## The Proof Scenario

**Scheme.** Define a symmetric encryption scheme as:

```
Enc(k, m)  =  (r, PRF(k, r) ⊕ m)    where r ←$ {0,1}^λ is fresh per call
Dec(k, (r, c))  =  PRF(k, r) ⊕ c
```

**Theorem.** `Enc` is IND-CPA secure if `PRF` is a secure pseudorandom function.

**Proof.** Via a two-hop game sequence:

```
G0 (Real)  ≈_PRF  G1  ≡  G2 (Ideal)
```

| Game | What changes in the LR oracle |
|------|-------------------------------|
| G0 — `IND-CPA.Real()` | Oracle computes `y ← PRF(k, r)`, returns `(r, y ⊕ m_b)` |
| G1 — Game 1 | Oracle samples `y ←$ {0,1}^λ` (random function), returns `(r, y ⊕ m_b)` |
| G2 — `IND-CPA.Ideal()` | Oracle samples `c ←$ {0,1}^λ` directly (message not used) |
| Red1 — Reduction `B` | Replaces `y` computation by querying an external PRF challenger |

## Files in This Directory

| File | Purpose |
|------|---------|
| `proof.yaml` | Declares the games, commentary, and figure specs (`package: nicodemus`) |
| `games_source.tex` | The single combined LaTeX source with `%:tags:` annotations |
| `macros.tex` | Five short macros (no external dependencies) |
| `nicodemus.sty` | The nicodemus pseudocode package |

---

## Key Differences from the cryptocode Tutorial

The YAML configuration (`proof.yaml`) is almost identical. The main differences are:

1. **`package: nicodemus`** is set at the top of the YAML.
2. **`nicodemus.sty`** is included in the `macros:` list (`.sty` files are copied to the
   build directory for `\usepackage` but are not `\input`-ed by the harness).

The source file (`games_source.tex`) has a different structure:

| cryptocode syntax | nicodemus syntax |
|-------------------|-----------------|
| `\begin{pcvstack}[boxed]` | `\begin{tabular}[t]{l}` + `\nicodemusboxNew{250pt}{%` |
| `\procedure[linenumbering]{Name}{` | `\textbf{Name}` |
| `k \getsr \{0,1\}^\lambda \\` | `\item $k \getsr \{0,1\}^\lambda$` |
| `\pcreturn (b' = b)` | `\item Return $(b' = b)$` |
| `}` (closing procedure) | `\end{nicodemus}%` |
| `\end{pcvstack}` | `}%` + `\end{tabular}%` |

**Key points:**
- **Text mode**: nicodemus environments are text-mode, so math content needs explicit `$...$`.
- **`\item` prefix**: Each pseudocode line starts with `\item` (nicodemus uses `enumerate`).
- **No `\\` separators**: nicodemus list items are naturally separated.
- **No `\pcreturn`**: Use plain text `Return` (with math parts in `$...$`).
- **Bold titles**: Procedure headers become `\textbf{...}` titles above `\begin{nicodemus}...\end{nicodemus}` blocks.

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
\item $k \getsr \{0,1\}^\lambda$ %:tags: G0-G2
```

### Consecutive variant lines encode "slots"

The `y` computation is a three-way slot:

```latex
\item $y \gets \mathrm{PRF}(k, r)$ %:tags: G0
\item $y \getsr \{0,1\}^\lambda$   %:tags: G1
\item $y \gets \OPRF(r)$           %:tags: Red1
```

### Procedure titles

In nicodemus, procedure titles are bold text labels above `\begin{nicodemus}` environments,
with one variant per game:

```latex
\textbf{$\INDCPA_\Enc^\Adversary.\mathsf{Real}()$} %:tags: G0
\textbf{Game~1} %:tags: G1
\textbf{$\INDCPA_\Enc^\Adversary.\mathsf{Ideal}()$} %:tags: G2
\textbf{Reduction $\Bdversary_1^{\OPRF}$} %:tags: Red1
```

Unlike cryptocode's `\procedure{...}{` syntax (which ends with `{` and is never wrapped
in `\tfchanged`), nicodemus bold titles **are** wrapped in `\tfchanged` when they change.

---

## Running the Tutorial

From the repo root:

```bash
# Generate per-game LaTeX files
texfrog latex tutorial-nicodemus/proof.yaml -o /tmp/tf_tutorial_nic

# Build an interactive HTML viewer
texfrog html build tutorial-nicodemus/proof.yaml -o /tmp/tf_tutorial_nic_html

# Or build and open immediately in your browser
texfrog html serve tutorial-nicodemus/proof.yaml
```

---

## What `\tfchanged` Looks Like

In the harness, the default highlight macro for nicodemus is:

```latex
\providecommand{\tfchanged}[1]{\colorbox{blue!15}{#1}}
```

Note: **no `$...$` wrapping** — unlike cryptocode, nicodemus content is text-mode, so
the highlight macro wraps content directly. The `\item` prefix is kept **outside**
`\tfchanged` to preserve the list structure:

```latex
\item \tfchanged{$y \getsr \{0,1\}^\lambda$}
```

---

## Next Steps

- Read [docs/writing-proofs.md](../docs/writing-proofs.md) for the complete reference on
  `proof.yaml` syntax and source-file constraints.
- See [tutorial-cryptocode/](../tutorial-cryptocode/) for the same proof using the `cryptocode` package (with a
  more detailed walkthrough of all TeXFrog concepts).
- See [example/](../example/) for a larger proof: a QSH IND-CCA argument with 12 games
  and reductions (using `cryptocode`).
- See [docs/latex-integration.md](../docs/latex-integration.md) for how to customise
  `\tfchanged` and `\tfgamelabel` in your paper.
