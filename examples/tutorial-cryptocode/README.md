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
| `proof.yaml` | Declares the games, commentary, and figure specs |
| `games_source.tex` | Combined LaTeX source with `%:tags:` annotations |
| `macros.tex` | Short macro definitions (no external dependencies) |

---

## Step 1 — The YAML Configuration (`proof.yaml`)

### `macros` and `source`

```yaml
macros:
  - macros.tex

source: games_source.tex
```

`macros` lists LaTeX files that define your proof-specific commands; `source` points to the combined pseudocode file. Both paths are relative to the YAML file.

### `games`

```yaml
games:
  - label: G0
    latex_name: 'G_0'
    description: '...'

  - label: Red1
    latex_name: '\Bdversary_1'
    description: '...'
    reduction: true

  - label: G1
    latex_name: 'G_1'
    description: '...'

  - label: G2
    latex_name: 'G_2'
    description: '...'

  - label: G3
    latex_name: 'G_3'
    description: '...'
```

Each game has a `label` (used in `%:tags:` and as the output filename), a `latex_name` (math-mode content without `$` delimiters), and a `description`. The optional `reduction: true` flag marks an entry as a reduction, which affects how it is displayed in the HTML viewer.

The order of the game list matters:

1. **Diffing.** TeXFrog highlights lines that differ between each game and the one before it. Red1 is diffed against G0, G1 against Red1, G2 against G1, G3 against G2.
2. **Range resolution.** Tags like `G0-G2` mean "from G0 to G2 by position in this list" — so `G0-G2` covers G0, Red1, G1, G2 (positions 0–3).

### `commentary`

```yaml
commentary:
  G1: |
    \begin{claim}
      Games~0 and~1 are indistinguishable assuming $\mathrm{PRF}$ is secure.
    \end{claim}
    ...
```

Each entry is raw LaTeX, written to `{label}_commentary.tex` and included by the harness after the game pseudocode. Use YAML's `|` (literal block) to preserve newlines.

### `figures`

```yaml
figures:
  - label: all_games
    games: "G0,G1,G2,G3,Red1"
    procedure_name: "Games $\\tfgamename{G0}$--$\\tfgamename{G3}$, Reduction $\\tfgamename{Red1}$"
```

This produces `fig_all_games.tex`: a consolidated block showing all five games, with game-specific lines annotated by `\tfgamelabel`. The optional `procedure_name` overrides the title of the first procedure header.

---

## Step 2 — The Combined Source (`games_source.tex`)

All pseudocode for all games lives in this one file. TeXFrog filters it per game.

### Lines with no tag appear in every game

```latex
b \getsr \{0,1\} \\
b' \gets \Adversary^{\mathsf{LR}}() \\
\pcreturn (b' = b)
```

These lines are identical across G0, G1, G2, G3, and Red1.

### Lines with a tag appear only in named games

```latex
k \getsr \{0,1\}^\lambda \\ %:tags: G0,G1-G3
```

The tag `G0,G1-G3` includes G0 (position 0) plus positions from G1 to G3 (positions 2–4): G1, G2, G3. Red1 (position 1) does not get this line.

### Consecutive variant lines encode "slots"

**This is the most important structural rule:** variant lines for the same logical slot must be consecutive in the source file. TeXFrog filters but never reorders lines.

The `y` computation is a four-way slot:

```latex
y \gets \mathrm{PRF}(k, r) \\ %:tags: G0
y \gets \RF(r) \\              %:tags: G1
y \getsr \{0,1\}^\lambda \\    %:tags: G2
y \gets \OPRF(r) \\            %:tags: Red1
```

For each game, at most one of these lines survives filtering. They are consecutive, so the chosen line always appears at the right position.

### Procedure headers

Here is how TeXFrog expects procedure headers to be typeset when using cryptocode:

```latex
\procedure[linenumbering]{\tfgamename{G0}}{ %:tags: G0
\procedure[linenumbering]{\tfgamename{G1}}{ %:tags: G1
\procedure[linenumbering]{\tfgamename{G2}}{ %:tags: G2
\procedure[linenumbering]{\tfgamename{G3}}{ %:tags: G3
\procedure[linenumbering]{\tfgamename{Red1}}{ %:tags: Red1
```

---

## Step 3 — Running the Tutorial

From the repo root:

```bash
# Generate per-game LaTeX files
texfrog latex examples/tutorial-cryptocode/proof.yaml -o /tmp/tf_tutorial_latex

# Build an interactive HTML viewer
texfrog html build examples/tutorial-cryptocode/proof.yaml -o /tmp/tf_tutorial_html

# Or build and open in your browser with live reload
texfrog html serve examples/tutorial-cryptocode/proof.yaml --live-reload
```

---

## Step 4 — Reading the Output

After running `texfrog latex`, the output directory contains:

```
G0.tex              — pseudocode for G0 (no highlighting; first game)
Red1.tex            — pseudocode for Red1; changed lines wrapped in \tfchanged{}
G1.tex              — pseudocode for G1; changed lines wrapped in \tfchanged{}
G2.tex              — pseudocode for G2; changed lines wrapped in \tfchanged{}
G3.tex              — pseudocode for G3; changed lines wrapped in \tfchanged{}
G0_commentary.tex   — LaTeX commentary for G0
...
proof_harness.tex   — \inputs macros, then each game + commentary in order
fig_all_games.tex   — consolidated figure with all five games annotated
```

Include the harness in your paper with `\input{proof_harness.tex}`, or include individual game files and figures as needed. See [LaTeX integration](../../docs/latex-integration.md) for details.

---

## Key Concepts Summary

| Concept | Where demonstrated |
|---------|-------------------|
| Untagged lines appear in every game | `b`, `b'`, `\pcreturn` lines |
| Single-game tag | `%:tags: G0`, `%:tags: G3` |
| Comma-separated tag list | `%:tags: G0,G1-G3` |
| Range tag | `%:tags: G0-G2` (positions 0–3, covers G0, Red1, G1, G2) |
| Consecutive variant slot | The four `y` lines; the two `c` lines |
| Changed-line highlighting | `y` highlighted in G1; `c` highlighted in G3 |
| Consolidated figure | `fig_all_games.tex` annotates game-specific lines |
| `\tfgamename` | Commentary uses `\tfgamename{G0}` to reference game names |

---

## Next Steps

- [Writing a proof](../../docs/writing-proofs.md) — full reference for `proof.yaml` and source file syntax
- [tutorial-nicodemus/](../tutorial-nicodemus/) — the same proof using the `nicodemus` package
- [LaTeX integration](../../docs/latex-integration.md) — customizing `\tfchanged` and `\tfgamelabel`
