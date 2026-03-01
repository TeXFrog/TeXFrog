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
.venv/bin/pytest tests/ -q       # 56 tests, should all pass
```

**Try the tool:**
```bash
.venv/bin/texfrog latex example/proof.yaml -o /tmp/tflatex
.venv/bin/texfrog html build example/proof.yaml -o /tmp/tfhtml
```

System requirements (not pip): `pdflatex`, `pdftocairo` (or `pdf2svg`), `pdfcrop`.

## Key Conventions

- **Tag syntax**: `%:tags: G1,G3-G5` at end of line — ranges resolved by position
  in the `games:` list, not alphabetically.
- **Source line ordering**: variant lines for the same "slot" must be consecutive;
  the tool filters but never reorders.
- **`\tfchanged` wrapping skips**: lines ending with `{` (procedure headers) and
  pure comment lines (starting with `%`).
- **Blank lines are stripped** from per-game `.tex` output to avoid `varwidth`
  dimension errors inside `pcvstack` environments.

## Critical HTML Build Gotchas

- Use `\documentclass{article}` — NOT `standalone` (incompatible with pcvstack).
- Do NOT use `\usepackage[active,tightpage]{preview}` — conflicts with `varwidth`.
- HTML wrapper `\tfchanged` must use `\ensuremath{#1}` — `\adjustbox` is text-mode
  but pseudocode content uses `\mathsf` etc.
- `pdftocairo -svg in.pdf out.svg` writes to the exact path given (no `.svg` appended).
- Files are copied to a flat temp dir before pdflatex — paths with spaces (this project
  lives in "Formal methods/") break `\input{}`.
