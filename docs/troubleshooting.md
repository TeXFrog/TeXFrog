# Troubleshooting & FAQ

Common problems proof authors encounter, organized by symptom. If your issue isn't listed here, run `texfrog check --strict proof.yaml` first — it catches many problems with clear error messages.

## Tag and Filtering Issues

### Lines are missing from a game

**Symptom:** A game is missing lines you expected to appear.

**Likely causes:**

1. **Typo in `%:tags:` label.** If you write `%:tags: G10` but the game is labeled `G1`, that line silently belongs to no game. Run `texfrog check --strict` — it warns about tags that don't match any game label:

   ```
   Warning: Tag 'G10' in source file does not match any game label. Typo?
   ```

2. **Wrong range endpoints.** Ranges are resolved by position in the `games:` list, not alphabetically. If your list is `G0, G1, Red2, G2`, then `%:tags: G1-G2` includes `G1`, `Red2`, *and* `G2`. Double-check that your range covers exactly the games you intend.

3. **Game has no tagged lines.** If a game only receives untagged (common) lines and you expected game-specific lines, verify the tags. `texfrog check --strict` warns:

   ```
   Warning: Game 'G3' has no tagged lines in the source (it only receives untagged common lines)
   ```

### `Range 'G5-G2' is reversed`

**Cause:** The start of the range comes *after* the end in the `games:` list. Ranges are positional — `G2-G5` means "from the position of G2 to the position of G5."

**Fix:** Swap the endpoints: `%:tags: G2-G5`.

### Game produces unexpected content or wrong line order

**Cause:** Variant lines for the same logical "slot" are not consecutive in the source file. TeXFrog filters but never reorders.

**Fix:** Group all alternatives for a slot together:

```latex
% Correct: variants are consecutive
(\ct_2^*, \key_2) \getsr \KEM_2.\encaps(\pk_2) \\   %:tags: G0
(\ct_2^*, \key_2^*) \getsr \KEM_2.\encaps(\pk_2) \\ %:tags: G1
(\ct_2^*, \_\_) \getsr \KEM_2.\encaps(\pk_2) \\     %:tags: G2-G9
```

If these were scattered in different parts of the file, each game would see them in the wrong position. See the [Source Ordering Constraint](writing-proofs.md#source-ordering-constraint) section in the writing guide.

### Tag range includes unexpected games (e.g., reductions)

**Cause:** Ranges include *everything* between the two endpoints by position, including reductions. Given the list `G0, G1, Red2, G2, G3`, the range `G1-G3` includes `G1`, `Red2`, `G2`, and `G3`.

**Fix:** This is by design — it lets reductions sit between games without breaking range syntax. If you need to exclude a reduction from a range, use an explicit comma-separated list instead: `%:tags: G1,G2,G3`.

## LaTeX Build Errors

### "Dimension too large" from pdflatex

**Cause:** Usually triggered by blank lines inside `pcvstack`/`varwidth` environments (a `cryptocode`-specific issue), or by conflicts with the `preview` package.

**Fixes:**

- **Do NOT** add `\usepackage[active,tightpage]{preview}` to your macro files — it conflicts with `varwidth`, which `pcvstack` uses internally.
- **Do NOT** use `\documentclass{standalone}` — it runs in LR mode, which is incompatible with `pcvstack`.
- TeXFrog automatically strips blank lines from per-game output to prevent this error. If you see it, check for manual edits to the generated `.tex` files, or for `preview`/`standalone` in your macros.

### "! LaTeX Error: File `...` not found"

**Likely causes:**

1. **Missing macro file.** Check that all files listed under `macros:` in your YAML exist at the specified relative paths. `texfrog check` warns about missing macro files.

2. **Path resolves outside the proof directory.** Paths like `../../../somewhere/macros.tex` that escape the proof directory are rejected:

   ```
   Error: Macro path '../../../lib/macros.tex' resolves outside the proof directory
   ```

   **Fix:** Keep all macro files within or below the directory containing `proof.yaml`.

3. **Spaces in file paths.** LaTeX's `\input{}` cannot handle paths with spaces. TeXFrog automatically copies files to a flat temporary directory before running pdflatex to work around this, but if you're running pdflatex manually on the generated files, ensure your paths don't contain spaces.

### Math mode errors (`\mathsf allowed only in math mode`)

**Cause:** Mismatch between the pseudocode package's mode and the `\tfchanged` definition. `cryptocode` content is in math mode; `nicodemus` content is in text mode.

**Fix:** Ensure your package profile is set correctly in `proof.yaml`. If you override `\tfchanged`, match the mode:

- **cryptocode:** `\newcommand{\tfchanged}[1]{\colorbox{blue!15}{$#1$}}`
- **nicodemus:** `\newcommand{\tfchanged}[1]{\colorbox{blue!15}{#1}}`

The HTML build wrapper handles this automatically. This error usually appears when a cryptocode proof's `\tfchanged` is defined without `$...$` wrapping, or when you accidentally set `package: nicodemus` for a cryptocode proof.

### `\item` appearing inside `\tfchanged`

**Cause:** This shouldn't happen — TeXFrog keeps `\item` prefixes outside `\tfchanged{}` for nicodemus to preserve list structure. If you see this, check that:

1. Your YAML has `package: nicodemus` set (not the default `cryptocode`).
2. You haven't manually edited the generated output files.

### Highlighting is not applied to some changed lines

**By design.** TeXFrog skips `\tfchanged` wrapping for:

- **Procedure headers** — lines ending with `{` (e.g., `\procedure{Name}{`). Wrapping these would break LaTeX brace matching.
- **Pure comment lines** — lines starting with `%`. These are invisible in the PDF.
- **Environment boundaries** — lines with `\begin{...}` or `\end{...}`.
- **Layout commands** — lines starting with `\markersetlen`.

## HTML Build Issues

### "pdflatex not found"

**Fix:** Install a TeX distribution:

- **macOS:** `brew install --cask mactex`
- **Linux:** `apt install texlive-full`

### "Neither pdftocairo nor pdf2svg found"

**Fix:** Install an SVG converter:

- **macOS:** `brew install poppler` (provides `pdftocairo`) or `brew install pdf2svg`
- **Linux:** `apt install poppler-utils` or `apt install pdf2svg`

### "Warning: pdfcrop not found"

This is a non-fatal warning. Without `pdfcrop`, SVG images will have wider margins but still render correctly.

**Fix:** Install `pdfcrop`:

- **macOS:** `brew install --cask mactex` (included with TeX Live)
- **Linux:** `apt install texlive-extra-utils`

### "pdflatex failed for game ..."

**Likely causes:**

1. **`preview` or `standalone` conflict** — see ["Dimension too large"](#dimension-too-large-from-pdflatex) above.
2. **Missing packages.** The HTML wrapper includes `amsfonts`, `amsmath`, `amsthm`, `adjustbox`, `xcolor`, and your selected pseudocode package. If your macros use additional packages (e.g., `stmaryrd`, `lmodern`), add them via the `preamble` field in your YAML:

   ```yaml
   preamble: preamble.tex
   ```

   where `preamble.tex` contains:

   ```latex
   \usepackage{stmaryrd}
   \usepackage{lmodern}
   ```

3. **Undefined commands in commentary.** Commentary is compiled through the same LaTeX pipeline as game pseudocode, so commands like `\newtheorem{claim}{Claim}` must be defined in your macros file.

### SVG images have wrong margins or sizes

**Cause:** `pdfcrop` is not installed, or a manual `\documentclass{standalone}` is interfering.

**Fix:** Install `pdfcrop` (see above) and ensure you're not using `standalone` document class in any of your macro files.

## YAML Configuration Errors

### `'games' list is required and must not be empty`

**Fix:** Your `proof.yaml` must have a non-empty `games:` section. Each game needs `label`, `latex_name`, and `description`.

### `'source' field (path to combined .tex file) is required`

**Fix:** Add a `source:` field pointing to your combined LaTeX source file:

```yaml
source: games_source.tex
```

### `Game label '...' contains unsafe characters`

**Fix:** Labels must match `[A-Za-z0-9_-]`. Use only letters, digits, hyphens, and underscores.

### `Unknown package profile '...'`

**Fix:** The `package:` field must be one of the supported profiles: `cryptocode` or `nicodemus`. Check for typos.

### `Game '...' has related_games but is not a reduction`

**Fix:** The `related_games` field is only valid on entries that also have `reduction: true`:

```yaml
- label: Red2
  latex_name: '\bdv_2'
  description: 'Reduction against IND-CCA security.'
  reduction: true              # required for related_games
  related_games: [G1, G2]
```

### `Reduction '...' has 3 related_games (maximum is 2)`

**Fix:** A reduction can reference at most 2 related games (for a 3-panel layout in the HTML viewer). Remove extra entries from the `related_games` list.

## `texfrog check` and Validation

### What does `texfrog check` validate?

`texfrog check` parses and validates your proof without building it. It checks:

- YAML structure (required fields, correct types)
- Game and figure label validity (safe characters, no duplicates)
- Source file existence and readability
- Macro file existence
- Tag labels (warns about tags that don't match any game)
- Tag ranges (catches reversed ranges)
- Game coverage (warns about games with no tagged lines or empty output)
- Reduction/related_games consistency
- Path safety (files don't escape the proof directory)

### What does `--strict` do?

Without `--strict`, warnings are displayed but the command exits successfully (exit code 0). With `--strict`, any warnings cause exit code 1. Use `--strict` in CI pipelines to catch potential problems early.

## FAQ

### Can I use labels other than G0, G1, etc.?

Yes. Labels are arbitrary strings matching `[A-Za-z0-9_-]`. Common patterns: `G0`–`G9`, `Red1`, `Hybrid3`, `BadEvent`, `Final`. The names are for your convenience — TeXFrog treats them as opaque identifiers.

### How do I add a reduction between two games?

Add it to the `games:` list at the position where it logically sits in the proof sequence. Set `reduction: true` and optionally `related_games`:

```yaml
games:
  - label: G1
    # ...
  - label: Red2
    latex_name: '\bdv_2'
    description: 'Reduction against IND-CCA security.'
    reduction: true
    related_games: [G1, G2]
  - label: G2
    # ...
```

Reductions are included in tag ranges — `G1-G2` in this example includes `Red2`.

### How do I suppress diff highlighting in the final paper?

Override `\tfchanged` to be a no-op in your preamble:

```latex
\renewcommand{\tfchanged}[1]{#1}
```

### Can I use custom `\tfchanged` / `\tfgamelabel` definitions?

Yes. The `texfrog.sty` package defines them with `\providecommand`, so you can override them with `\renewcommand` in your preamble.

### Why does `latex_name` not include `$` delimiters?

Because `latex_name` is used in multiple contexts — `\ensuremath` in LaTeX (which handles math mode automatically) and `$...$` in the HTML viewer (for MathJax). Including `$` in the YAML would double-wrap in some contexts.

### Why are blank lines stripped from output?

Blank lines inside `varwidth` environments (used by cryptocode's `pcvstack`) can cause "Dimension too large" errors. TeXFrog strips them to prevent this. If you need visual spacing, use `\vspace` or similar LaTeX commands on a tagged line.

### My live-reload isn't picking up changes to a new file

The file watcher monitors paths listed in your `proof.yaml` (source, macros, preamble, commentary files). After adding a new file to `macros:` or `commentary:` in the YAML, save the YAML file — the watcher refreshes its file set after each rebuild.
