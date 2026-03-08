# TeXFrog — Claude Instructions

See `docs/system-design.md` for full architecture, algorithms, and implementation notes.

## Quick Reference

**Dev setup** (venv already exists at `.venv/`):
```bash
source .venv/bin/activate.fish   # fish shell
pip install -e ".[dev]"          # if reinstall needed
```

**Run tests:**
```bash
.venv/bin/pytest tests/ -q                          # Python tests (226 tests)
cd vscode-texfrog && npm test                       # VS Code extension tests (35 tests)
```

**Try the tool:**
```bash
.venv/bin/texfrog check examples/tutorial-cryptocode-quickstart/main.tex
.venv/bin/texfrog html build examples/tutorial-cryptocode-quickstart/main.tex -o /tmp/tfhtml
.venv/bin/texfrog html serve examples/tutorial-cryptocode-quickstart/main.tex -o /tmp/tfhtml

# Scaffold a new proof
.venv/bin/texfrog init /tmp/tfinit                        # cryptocode (default)
.venv/bin/texfrog init /tmp/tfinit-nic --package nicodemus # nicodemus variant
```

System requirements (not pip): `pdflatex`, `pdftocairo` (or `pdf2svg`), `pdfcrop`.

## Input Format

The `.tex` file is the single source of truth. It uses the `texfrog.sty` LaTeX package
for compilation and is parsed by `texfrog/tex_parser.py` for HTML export.

Key commands (most take a `source` name as their first argument to support
multiple proofs per document):
- `\tfgames{source}{games}`, `\tfgamename{source}{label}{name}` (define),
  `\tfdescription{source}{label}{desc}`, `\tfreduction{source}{label}`,
  `\tfrelatedgames{source}{label}{games}`, `\tfcommentary{source}{label}{file}`,
  `\tffigure{source}[opt]{label}{games}`
- `\tfgamename{label}` (1-arg lookup inside `tfsource` body, uses active source)
- Unchanged (no source arg): `\tfmacrofile{path}`, `\tfpreamble{path}`,
  `\tfonly{tags}{content}`, `\tfonly*{tags}{content}`, `\tffigonly{content}`,
  `\tfrendergame[opt]{source}{game}`, `\tfrenderfigure{source}{games}`,
  `\begin{tfsource}{name}...\end{tfsource}`

Package option: `\usepackage[package=cryptocode]{texfrog}` or `package=nicodemus`.

## Key Conventions

- **Package profiles**: `\usepackage[package=cryptocode]{texfrog}` (default) or `nicodemus`.
  Profiles are defined in `texfrog/packages.py`.
- **Tag syntax**: `\tfonly{G1,G3-G5}{content}`. Ranges resolved by position
  in the games list, not alphabetically.
- **`\tfchanged` wrapping skips**: lines ending with `{` (procedure headers) and
  pure comment lines (starting with `%`). For nicodemus, `\item` prefix is kept
  outside `\tfchanged{}`.
- **`latex_name` is math-mode content** without `$` delimiters. `\tfgamename{source}{label}`
  (or 1-arg `\tfgamename{label}` inside `tfsource`) wraps it in `\ensuremath` (LaTeX)
  or `$...$` (HTML/MathJax).
- **Blank lines are stripped** from per-game `.tex` output to avoid `varwidth`
  dimension errors inside `pcvstack` environments.

## Critical HTML Build Gotchas

- Use `\documentclass{article}` — NOT `standalone` (incompatible with pcvstack).
- Do NOT use `\usepackage[active,tightpage]{preview}` — conflicts with `varwidth`.
- HTML wrapper `\tfchanged` uses `\ifmmode` to detect math vs text context:
  in math mode wraps with `\ensuremath`, in text mode passes through directly.
  This allows wrapping both procedure body content (math) and title content (text).
- `pdftocairo -svg in.pdf out.svg` writes to the exact path given (no `.svg` appended).
- Files are copied to a flat temp dir before pdflatex — paths with spaces break `\input{}`.

## When Making Changes

- **Update user documentation**: When adding or changing features, update the relevant
  docs (e.g., `docs/*.md`, tutorial READMEs, example files) to reflect the new behavior.
- **Write unit tests**: For any new feature or bug fix, add both positive tests
  (expected behavior works correctly) and negative tests (invalid input is rejected
  with appropriate errors/warnings) in `tests/`.
