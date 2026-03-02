#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEXFROG="${SCRIPT_DIR}/.venv/bin/texfrog"

for tutorial in tutorial-cryptocode tutorial-nicodemus; do
    echo "=========================================="
    echo "Building ${tutorial}"
    echo "=========================================="

    yaml="${SCRIPT_DIR}/${tutorial}/proof.yaml"

    echo "--- Generating LaTeX ---"
    "$TEXFROG" latex "$yaml"

    echo "--- Building HTML ---"
    "$TEXFROG" html build "$yaml"

    echo "--- Copying support files for pdflatex ---"
    cp "${SCRIPT_DIR}/${tutorial}/main.tex" "${SCRIPT_DIR}/${tutorial}/texfrog_latex/"
    cp "${SCRIPT_DIR}/${tutorial}/macros.tex" "${SCRIPT_DIR}/${tutorial}/texfrog_latex/"
    if [ "${tutorial}" = "tutorial-nicodemus" ]; then
        cp "${SCRIPT_DIR}/${tutorial}/nicodemus.sty" "${SCRIPT_DIR}/${tutorial}/texfrog_latex/"
    fi

    echo "--- Compiling main.tex ---"
    (cd "${SCRIPT_DIR}/${tutorial}/texfrog_latex" && pdflatex -interaction=nonstopmode main.tex)

    echo ""
done

echo "All tutorials built successfully."
echo ""
echo "Generated PDFs:"
echo "  ${SCRIPT_DIR}/tutorial-cryptocode/texfrog_latex/main.pdf"
echo "  ${SCRIPT_DIR}/tutorial-nicodemus/texfrog_latex/main.pdf"
echo ""
echo "Generated webpages (open in a web browser):"
echo "  ${SCRIPT_DIR}/tutorial-cryptocode/texfrog_html/index.html"
echo "  ${SCRIPT_DIR}/tutorial-nicodemus/texfrog_html/index.html"
