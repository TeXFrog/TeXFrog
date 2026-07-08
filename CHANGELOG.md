# Changelog

## Unreleased

### New features

- **`algpseudocodex` package profile.** `\usepackage[package=algpseudocodex]{texfrog}`
  and `texfrog init --package algpseudocodex` scaffold proofs using the `algpseudocodex`
  package's `\State`/`\Statex`-based pseudocode, alongside the existing `cryptocode` and
  `nicodemus` profiles. `\tfchanged` keeps the `\State` prefix outside the highlight box
  (as it already did for `nicodemus`'s `\item`), and wraps highlighted text in a
  `varwidth` matching the remaining line width, so changed-line highlighting renders and
  wraps correctly inside algpseudocodex's per-line `varwidth` layout.

### Bug fixes

- **Tall games no longer render as blank SVGs in `texfrog html`.** Games taller
  than one page previously overflowed onto a 2nd page, making `pdftocairo -svg`
  emit a non-standard multi-page `<pageSet>`/`<page>` wrapper that browsers
  silently fail to render. The wrapper page height is now 200in (width
  unchanged) so games stay on a single page, with a `pdfinfo`-based guard that
  raises a clear error instead of producing a broken SVG if one still overflows.
- **Unknown `package=` values now warn instead of silently falling back.** An invalid
  `\usepackage[package=...]{texfrog}` value previously hit l3keys' generic "accepts only
  a fixed set of choices" error with no indication of what happened or what the valid
  choices are. It now emits a clear texfrog warning naming the valid choices and falls
  back to `cryptocode`.
- **`texfrog init --package nicodemus` is now self-contained.** The scaffold bundles
  `nicodemus.sty` (which is not on CTAN) and registers it with `\tfmacrofile`, so the
  generated proof compiles with `pdflatex` and renders with `texfrog html build`
  without a system-wide nicodemus install.
- **`\tfrendergame[diff=...]` highlighting was broken.** Two bugs in `texfrog.sty` made diff rendering mark every `\tfonly` line as changed and (with `algpseudocodex`) render changed lines as empty highlight boxes:
  - The diff target game label was stored as the unexpanded `\l__tf_diff_tl` token, so the recording pass never matched any tags and the recorded-positions property list stayed empty.
  - The highlight wrapper emitted its prefix (`\State`) before reading its local content variable. In `algpseudocodex`, `\State` closes the `varwidth` group of the previous line, reverting the local assignments and emptying the content. The wrapper output is now assembled in a global token list and emitted in a single expansion.
## v0.0.2

### Breaking changes

- **Pure LaTeX input format.** The `.tex` file is now the single source of truth. The YAML input pipeline and `texfrog latex` command have been removed. Proofs are authored using the `texfrog.sty` LaTeX package directly.
- **Package selection moved to `\usepackage` option.** Use `\usepackage[package=cryptocode]{texfrog}` instead of `\tfsetpackage{cryptocode}`.

### New features

- **`texfrog.sty` LaTeX package.** An expl3-based package (`latex/texfrog.sty`) that handles game rendering at compile time, eliminating the need for a separate LaTeX generation step.
- **Multiple proofs per document.** A single `.tex` file can now contain multiple independent proofs using source-scoped commands (e.g., `\tfgames{source}{...}`).
- **VS Code extension.** New extension (`vscode-texfrog`) provides game-based line dimming, with a game picker grouped by source for multi-proof documents.
- **HTML viewer improvements:**
  - Overview landing page with all game transitions at a glance.
  - Print-friendly view.
  - Responsive layout with collapsible sidebar for mobile and medium-width viewports.
  - Side-by-side game display on mobile when space permits.
  - Live-reload is now the default for `html serve`.
  - Browser back/forward navigation now updates the viewer correctly.
- **New LaTeX commands:**
  - `\tfonly*{tags}{content}` and `\tffigonly{content}` for figure headers with suppressed highlighting.
  - `\tfrendergame` now defaults to no highlighting; use `diff=` option for change highlighting.
- **Scaffold command.** `texfrog init` scaffolds a new proof directory with either `cryptocode` (default) or `nicodemus` package profiles.

## v0.0.1

Initial release.
