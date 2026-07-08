# Changelog

## Unreleased

### Bug fixes

- **Tall games no longer render as blank SVGs in `texfrog html`.** Games taller
  than one page previously overflowed onto a 2nd page, making `pdftocairo -svg`
  emit a non-standard multi-page `<pageSet>`/`<page>` wrapper that browsers
  silently fail to render. The wrapper page height is now 200in (width
  unchanged) so games stay on a single page, with a `pdfinfo`-based guard that
  raises a clear error instead of producing a broken SVG if one still overflows.
- **`texfrog init --package nicodemus` is now self-contained.** The scaffold bundles
  `nicodemus.sty` (which is not on CTAN) and registers it with `\tfmacrofile`, so the
  generated proof compiles with `pdflatex` and renders with `texfrog html build`
  without a system-wide nicodemus install.

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
