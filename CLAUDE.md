# TeXFrog — Claude Instructions

See `DESIGN.md` for full architecture, algorithms, and implementation notes.

## Quick Reference

**Dev setup** (venv already exists at `.venv/`):
```bash
source .venv/bin/activate.fish   # fish shell
pip install -e ".[dev]"          # if reinstall needed
```

**Run tests:**
```bash
.venv/bin/pytest tests/ -q       # 100 tests, should all pass
```

**Try the tool:**
```bash
.venv/bin/texfrog init /tmp/tfinit                        # scaffold a new proof
.venv/bin/texfrog init /tmp/tfinit-nic --package nicodemus # nicodemus variant
.venv/bin/texfrog latex example/proof.yaml -o /tmp/tflatex
.venv/bin/texfrog html build example/proof.yaml -o /tmp/tfhtml
.venv/bin/texfrog latex tutorial-cryptocode/proof.yaml -o /tmp/tflatex-tutorial
.venv/bin/texfrog latex tutorial-nicodemus/proof.yaml -o /tmp/tflatex-tutorial-nic
.venv/bin/texfrog html serve --live-reload tutorial-cryptocode/proof.yaml -o /tmp/tfhtml
```

System requirements (not pip): `pdflatex`, `pdftocairo` (or `pdf2svg`), `pdfcrop`.

## Key Conventions

- **Package profiles**: `package: cryptocode` (default) or `package: nicodemus` in
  proof.yaml. Profiles are defined in `texfrog/packages.py`.
- **Tag syntax**: `%:tags: G1,G3-G5` at end of line — ranges resolved by position
  in the `games:` list, not alphabetically.
- **Source line ordering**: variant lines for the same "slot" must be consecutive;
  the tool filters but never reorders.
- **`\tfchanged` wrapping skips**: lines ending with `{` (procedure headers) and
  pure comment lines (starting with `%`). For nicodemus, `\item` prefix is kept
  outside `\tfchanged{}`.
- **`latex_name` is math-mode content** without `$` delimiters. `\tfgamename{label}`
  wraps it in `\ensuremath` (LaTeX) or `$...$` (HTML/MathJax).
- **Blank lines are stripped** from per-game `.tex` output to avoid `varwidth`
  dimension errors inside `pcvstack` environments.
- **.sty/.cls files** in `macros:` are copied but not `\input`'d (loaded via `\usepackage`).

## Critical HTML Build Gotchas

- Use `\documentclass{article}` — NOT `standalone` (incompatible with pcvstack).
- Do NOT use `\usepackage[active,tightpage]{preview}` — conflicts with `varwidth`.
- HTML wrapper `\tfchanged` uses `\ensuremath{#1}` for cryptocode (math-mode content)
  but plain `{#1}` for nicodemus (text-mode content). This is handled automatically
  by the package profile.
- `pdftocairo -svg in.pdf out.svg` writes to the exact path given (no `.svg` appended).
- Files are copied to a flat temp dir before pdflatex — paths with spaces (this project
  lives in "Formal methods/") break `\input{}`.
