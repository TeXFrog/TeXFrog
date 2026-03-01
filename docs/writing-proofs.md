# Writing a Proof for TeXFrog

TeXFrog reads two input files: a YAML configuration file (`proof.yaml`) and a combined LaTeX source file (`games_source.tex`). This guide explains both.

## Overview

A game-hopping proof consists of a sequence of games (and reductions). Adjacent games usually differ by only a few lines of pseudocode. TeXFrog exploits this by letting you write all games in a single source file, tagging each line with the games it belongs to. Lines without a tag appear in every game.

## The YAML Configuration File

The YAML file has five sections: `macros`, `source`, `games`, `commentary`, and `figures`.

### `macros`

A list of LaTeX files containing macro definitions, relative to the YAML file's location.

```yaml
macros:
  - macros.tex
  - ../shared/crypto-macros.tex
```

These files are `\input`-ed into the HTML compilation and into the generated harness. You can list as many as you need.

### `source`

The path to the combined LaTeX source file, relative to the YAML file.

```yaml
source: games_source.tex
```

### `games`

An ordered list of all games and reductions. The order here is the canonical sequence of the proof — it determines which games are "adjacent" for diff highlighting, and it defines what tag ranges like `G0-G5` mean.

Each entry has the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| `label` | yes | Short identifier used in `%:tags:` comments and as the output filename stem (e.g. `G0`, `Red2`) |
| `latex_name` | yes | Math-mode LaTeX for the game name, without `$` delimiters (e.g. `'G_1'` or `'\indcca_\QSH^\adv.\REAL()'`). Rendered via `\ensuremath` in LaTeX and `$...$` in the HTML viewer. |
| `description` | yes | A one-sentence LaTeX description shown in the HTML viewer |
| `reduction` | no | Set to `true` for reductions. In the HTML viewer, reductions are displayed alone rather than side-by-side with the previous game (unless `related_games` is set). Defaults to `false`. |
| `related_games` | no | A list of zero, one, or two game labels. Only valid when `reduction: true`. In the HTML viewer, clean (unhighlighted) versions of these games are shown alongside the reduction: one related game gives a 2-panel layout, two gives a 3-panel layout with the reduction in the middle. |

```yaml
games:
  - label: G0
    latex_name: '\indcca_\QSH^\adv.\REAL()'
    description: 'The starting game (real IND-CCA game).'

  - label: G1
    latex_name: 'G_1'
    description: 'Replace $\key_2$ with a fresh $\key_2^*$ from encapsulation.'

  - label: Red2
    latex_name: '\bdv_2'
    description: 'Reduction against $\indcca$ security of $\KEM_2$.'
    reduction: true
    related_games: [G0, G1]

  - label: G2
    latex_name: 'G_2'
    description: 'Replace challenge key $\key_2^*$ with a uniformly random value.'
```

Labels can be anything: `G0`, `Red2`, `Hybrid3`, `BadEvent` — TeXFrog treats them as arbitrary strings.

### `commentary` (optional)

Free-form LaTeX text for each game, keyed by label. This text is written to `{label}_commentary.tex` and `\input`-ed into the harness after the game pseudocode.

```yaml
commentary:
  G0: |
    The starting game is $\indcca_\QSH^\adv.\REAL()$.

  G1: |
    \begin{claim}
      Games~0 and~1 are indistinguishable assuming correctness of $\KEM_2$.
    \end{claim}
    This follows by inlining the decapsulation result.
```

Use YAML's literal block scalar (`|`) to preserve newlines. LaTeX environments, math, and display equations all work here. You can use `\tfgamename{G1}` to reference a game's `latex_name` — see [latex-integration.md](latex-integration.md).

**HTML viewer:** Commentary is compiled through the same LaTeX → PDF → SVG pipeline as game pseudocode, so any LaTeX commands or environments used in commentary (e.g., `\newtheorem{claim}{Claim}`) must be defined in your macros file. The packages available in the HTML compilation wrapper are: `cryptocode`, `amsfonts`, `amsmath`, `amsthm`, `adjustbox`, and `xcolor`.

### `figures` (optional)

A list of consolidated figures showing multiple games side by side, for use as comparison tables in your paper.

```yaml
figures:
  - label: start_end
    games: "G0,G9"

  - label: main_proof
    games: "G0-G2,G8,G9"
```

Each figure has:
- `label` — used as the output filename: `fig_{label}.tex`
- `games` — comma-separated list or range of game labels (same syntax as `%:tags:`)

In the generated figure, lines that appear in all selected games are output verbatim. Lines that appear in only some games are annotated with `\tfgamelabel{G1,G3}{line content}`. See [latex-integration.md](latex-integration.md) for customizing the annotation macro.

## The Combined LaTeX Source File

The source file contains the pseudocode for all games merged together, with each line optionally tagged.

### Tag Syntax

Place a `%:tags:` comment at the end of a line to restrict it to specific games:

```latex
% This line appears in every game (no tag):
(\pk_1, \sk_1) \getsr \KEM_1.\keygen() \\

% This line appears only in G0:
(\ct_2^*, \key_2) \getsr \KEM_2.\encaps(\pk_2) \\ %:tags: G0

% This line appears in G1 through G4 and also in Red2:
(\ct_1^*, \key_1) \getsr \KEM_1.\encaps(\pk_1) \\ %:tags: G1-G4,Red2
```

Tag syntax:
- **Single label**: `%:tags: G0`
- **Comma-separated list**: `%:tags: G0,G3,Red2`
- **Range**: `%:tags: G0-G9` — includes all games from G0 to G9 *by position in the games list*
- **Mixed**: `%:tags: G0,G3-G5,Red2`

### Range Resolution

Ranges are resolved **positionally** — by the order games appear in the YAML file, not alphabetically or numerically. Given the game list `G0, G1, G2, Red2, G3, G4`, the tag `%:tags: G1-G3` includes `G1`, `G2`, `Red2`, and `G3`, because `Red2` sits between `G2` and `G3` in the sequence.

This lets you insert reductions (e.g. `Red2`) between games without breaking range syntax.

Unknown labels in tags are silently ignored, so a typo like `%:tags: G10` when `G10` doesn't exist will simply cause the line to appear in no game.

### Source Ordering Constraint

**This is the most important constraint in TeXFrog.**

Variant lines for the same logical "slot" — lines that are alternatives of each other in different games — must be **consecutive** in the source file. TeXFrog filters lines but does not reorder them.

For example, the KEM_2 encaps line varies across games:

```latex
% Correct: variants are consecutive
(\ct_2^*, \key_2) \getsr \KEM_2.\encaps(\pk_2) \\ %:tags: G0
(\ct_2^*, \key_2^*) \getsr \KEM_2.\encaps(\pk_2) \\ %:tags: G1
(\ct_2^*, \_\_) \getsr \KEM_2.\encaps(\pk_2) \\ %:tags: G2-G9
```

If you placed these in different parts of the file, they would all appear together at the wrong point in the filtered output. Keep variants for the same slot consecutive.

### Lines That Are Not Wrapped in `\tfchanged`

When generating the LaTeX output, TeXFrog wraps changed lines in `\tfchanged{}` to highlight them. Two kinds of lines are never wrapped, even if they changed:

- **Procedure headers**: lines ending with `{` (e.g. `\procedure{Name}{`). Wrapping these would break LaTeX brace matching.
- **Pure comment lines**: lines that start with `%`. These are invisible in the PDF, so wrapping them is pointless.

### Tips for Writing the Source

**Structure your source top-to-bottom** in the same order the pseudocode will appear in the rendered games. The file is essentially the pseudocode of any single game, with variant lines for other games interleaved.

**Use comments to label sections.** The source file is read by both you and TeXFrog. Comments like `%%% --- Oracle section ---` help orient readers and are harmless (comment lines are never wrapped).

**One game header per game.** If you use `\procedure` environments, put each game's procedure header (a line ending with `{`) as a tagged line so only the right header appears in each game:

```latex
\procedure[linenumbering]{Starting game $= \indcca_\QSH^\adv.\REAL()$}{ %:tags: G0
\procedure[linenumbering]{Game~1}{ %:tags: G1
\procedure[linenumbering]{Game~2}{ %:tags: G2
```

**Avoid blank lines between tagged variants.** Only untagged blank lines appear in the output; tagged blank lines are excluded with their game. Blank lines in output are stripped regardless to prevent `varwidth` dimension errors in pseudocode environments like `pcvstack`.

## Complete Example

The `example/` directory contains a full worked example: a QSH IND-CCA proof with 12 entries (G0–G9, Red2, Red5).

- [example/proof.yaml](../example/proof.yaml) — the YAML config
- [example/games_source.tex](../example/games_source.tex) — the combined source

To try it:

```bash
texfrog latex example/proof.yaml -o /tmp/tf_latex
texfrog html serve example/proof.yaml
```
