# TeXFrog Tutorial

This tutorial walks through a small, complete proof to introduce every TeXFrog concept.
The proof is short enough to read in full, but exercises every feature of the tool.

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

G0 → G1 is by PRF security (via `Red1`). G1 → G2 is a perfect equivalence: `y ⊕ m_b` with
uniform `y` is uniform regardless of `m_b`, so we can sample `c` directly.

## Files in This Directory

| File | Purpose |
|------|---------|
| `proof.yaml` | Declares the games, commentary, and figure specs |
| `games_source.tex` | The single combined LaTeX source with `%:tags:` annotations |
| `macros.tex` | Five short macros (no external dependencies) |

---

## Step 1 — The YAML Configuration (`proof.yaml`)

The YAML file has four active sections: `macros`, `source`, `games`, and `commentary`.

### `macros` and `source`

```yaml
macros:
  - macros.tex

source: games_source.tex
```

`macros` lists LaTeX files that define your proof-specific commands; `source` points to the
combined pseudocode file. Both paths are relative to the YAML file.

### `games`

```yaml
games:
  - label: G0
    latex_name: 'G_0'
    description: '...'

  - label: G1
    latex_name: 'G_1'
    description: '...'

  - label: G2
    latex_name: 'G_2'
    description: '...'

  - label: Red1
    latex_name: '\Bdversary_1'
    description: '...'
    reduction: true
```

The optional `reduction: true` flag marks an entry as a reduction. In the HTML viewer,
reductions are displayed alone rather than side-by-side with the previous game.

The `latex_name` is math-mode content without `$` delimiters. TeXFrog wraps it in `\ensuremath` (LaTeX) or `$...$` (HTML/MathJax) automatically. You can reference any game's name in commentary or your paper with `\tfgamename{G1}`.

The order here matters in two ways:

1. **Adjacent-game diffing.** TeXFrog highlights lines that differ between each game and
   the one before it. G1 is diffed against G0, G2 against G1, Red1 against G2.

2. **Range resolution.** Tags like `G0-G2` mean "from G0 to G2 by position in this list"
   — so `G0-G2` covers G0, G1, G2 and excludes Red1 (which is at position 3).

### `commentary`

```yaml
commentary:
  G1: |
    \begin{claim}
      Games~0 and~1 are indistinguishable assuming $\mathrm{PRF}$ is secure.
    \end{claim}
    ...
```

Each entry is raw LaTeX written to `{label}_commentary.tex` and `\input`-ed by the harness
immediately after the game pseudocode. Use YAML's `|` (literal block) to preserve newlines.

### `figures`

```yaml
figures:
  - label: all_games
    games: "G0,G1,G2,Red1"
```

This produces `fig_all_games.tex`: a single consolidated block showing all four games
side by side, with game-specific lines annotated by `\tfgamelabel`.

---

## Step 2 — The Combined Source (`games_source.tex`)

All pseudocode for all games lives in this one file. TeXFrog filters it per game.

### Lines with no tag appear in every game

```latex
b \getsr \{0,1\} \\
b' \gets \Adversary^{\mathsf{LR}}() \\
\pcreturn (b' = b)
```

These three lines — sampling the challenge bit, running the adversary, and returning
the result — are identical across G0, G1, G2, and Red1. Writing them once with no
tag is all that is needed.

### Lines with a tag appear only in named games

```latex
k \getsr \{0,1\}^\lambda \\ %:tags: G0-G2
```

The range `G0-G2` resolves to positions 0–2 in the games list: G0, G1, G2.
Red1 (position 3) does not receive this line — it has no PRF key because it queries
an external challenger instead.

### Consecutive variant lines encode "slots"

The most important structural rule: **variant lines for the same logical slot must be
consecutive in the source file.** TeXFrog filters but never reorders lines.

Here the `y` computation is a three-way slot:

```latex
y \gets \mathrm{PRF}(k, r) \\ %:tags: G0
y \getsr \{0,1\}^\lambda \\   %:tags: G1
y \gets \OPRF(r) \\           %:tags: Red1
```

For each game, exactly one of these three lines survives filtering. They are consecutive
in the source, so the chosen line always appears at the right position in the output.
In G2, none of them survive — the `c` slot that follows handles G2 directly:

```latex
c \gets y \oplus m_b \\ %:tags: G0,G1,Red1
c \getsr \{0,1\}^\lambda \\ %:tags: G2
```

### Procedure headers

Lines ending with `{` are treated as procedure headers. They are never wrapped in
`\tfchanged` (wrapping would break LaTeX brace matching) and they collapse to a single
header in consolidated figures.

```latex
\procedure[linenumbering]{\tfgamename{G0}}{ %:tags: G0
\procedure[linenumbering]{\tfgamename{G1}}{ %:tags: G1
\procedure[linenumbering]{\tfgamename{G2}}{ %:tags: G2
\procedure[linenumbering]{\tfgamename{Red1}}{ %:tags: Red1
```

Each game sees exactly one of these four headers.

---

## Step 3 — Running the Tutorial

From the repo root:

```bash
# Generate per-game LaTeX files
texfrog latex tutorial/proof.yaml -o /tmp/tf_tutorial

# Build an interactive HTML viewer
texfrog html build tutorial/proof.yaml -o /tmp/tf_tutorial_html

# Or build and open immediately in your browser
texfrog html serve tutorial/proof.yaml
```

---

## Step 4 — Reading the Output

After running `texfrog latex`, the output directory contains:

```
G0.tex              — pseudocode for G0 (no highlighting; it is the first game)
G1.tex              — pseudocode for G1; changed lines wrapped in \tfchanged{}
G2.tex              — pseudocode for G2; changed lines wrapped in \tfchanged{}
Red1.tex            — pseudocode for Red1; changed lines wrapped in \tfchanged{}
G0_commentary.tex   — LaTeX commentary text for G0
...
proof_harness.tex   — \inputs macros, then each game file + commentary in order
fig_all_games.tex   — consolidated figure with all four games annotated
```

### What changed in each game?

| Output file | Highlighted lines |
|-------------|------------------|
| `G1.tex` | `y ←$ {0,1}^λ` (replaced PRF call) |
| `G2.tex` | `c ←$ {0,1}^λ` (replaced `y ⊕ m_b`) |
| `Red1.tex` | `y ← OPRF(r)` and `c ← y ⊕ m_b` (both absent from G2, so both are "new") |

### The consolidated figure

`fig_all_games.tex` shows all four games in one pseudocode block. Lines that appear in
all four games are printed verbatim; lines that appear in only some are annotated:

```latex
\tfgamelabel{\tfgamename{G0},\tfgamename{G1},\tfgamename{G2}}{        k \getsr \{0,1\}^\lambda} \\
\tfgamelabel{\tfgamename{G0}}{        y \gets \mathrm{PRF}(k, r)} \\
\tfgamelabel{\tfgamename{G1}}{        y \getsr \{0,1\}^\lambda} \\
\tfgamelabel{\tfgamename{Red1}}{        y \gets \OPRF(r)} \\
\tfgamelabel{\tfgamename{G0},\tfgamename{G1},\tfgamename{Red1}}{        c \gets y \oplus m_b} \\
\tfgamelabel{\tfgamename{G2}}{        c \getsr \{0,1\}^\lambda} \\
```

The first argument of `\tfgamelabel` uses `\tfgamename` to display the rendered game names (e.g., `$G_0$` instead of the raw label `G0`). The default `\tfgamelabel` definition appends these names as a pseudocode comment. Override it in your paper to match your house style.

### Using the output in your paper

`\input` the harness into your paper's LaTeX source:

```latex
\input{/path/to/output/proof_harness.tex}
```

Or `\input` individual game files and figures as needed. See
[docs/latex-integration.md](../docs/latex-integration.md) for full details.

---

## Key Concepts Summary

| Concept | Where demonstrated |
|---------|-------------------|
| Untagged lines appear in every game | `b ←$ {0,1}`, `\pcreturn (b' = b)`, `r ←$ {0,1}^λ` |
| Single-game tag | `%:tags: G0`, `%:tags: G2` |
| Explicit list tag | `%:tags: G0,G1,Red1` |
| Range tag | `%:tags: G0-G2` (positions 0–2, excludes Red1) |
| Consecutive variant slot | The three `y` computation lines; the two `c` computation lines |
| Reduction sharing structure | Red1 main body is identical to G0/G1/G2 except `k` is absent |
| Changed-line highlighting | `y ←$ {0,1}^λ` highlighted in G1; `c ←$ {0,1}^λ` highlighted in G2 |
| Consolidated figure | `fig_all_games.tex` annotates every game-specific line |
| `\tfgamename` | Commentary uses `\tfgamename{G0}` to reference game names portably |

---

## Next Steps

- Read [docs/writing-proofs.md](../docs/writing-proofs.md) for the complete reference on
  `proof.yaml` syntax and source-file constraints.
- See [example/](../example/) for a larger proof: a QSH IND-CCA argument with 12 games
  and reductions.
- See [docs/latex-integration.md](../docs/latex-integration.md) for how to customise
  `\tfchanged` and `\tfgamelabel` in your paper.
