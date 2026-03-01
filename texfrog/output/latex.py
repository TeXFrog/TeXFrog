"""LaTeX output generators for TeXFrog."""

from __future__ import annotations

from pathlib import Path

from ..filter import compute_changed_lines, filter_for_game, wrap_changed_line
from ..model import Proof

# Macro used to highlight changed lines.
_CHANGED_MACRO = r"\tfchanged"

# Macro used to annotate game-specific lines in consolidated figures.
_GAMELABEL_MACRO = r"\tfgamelabel"


def _write_game_file(
    game_label: str,
    current_lines: list[str],
    changed_indices: set[int],
    out_path: Path,
) -> None:
    """Write per-game LaTeX file with changed lines highlighted.

    Args:
        game_label: The game/reduction label (used only in a leading comment).
        current_lines: Filtered content lines for this game.
        changed_indices: 0-based indices of lines to wrap with ``\\tfchanged``.
        out_path: Destination file path.
    """
    parts: list[str] = [f"% TeXFrog output for game: {game_label}\n"]
    for i, line in enumerate(current_lines):
        # Skip blank lines — they arise from excluded tagged content and can
        # cause LaTeX dimension errors inside pseudocode environments
        # (e.g. varwidth used internally by cryptocode's pcvstack).
        if not line.strip():
            continue
        if i in changed_indices:
            parts.append(wrap_changed_line(line, _CHANGED_MACRO) + "\n")
        else:
            parts.append(line + "\n")
    out_path.write_text("".join(parts), encoding="utf-8")


def _write_commentary_file(game_label: str, text: str, out_path: Path) -> None:
    """Write a per-game commentary LaTeX file.

    Args:
        game_label: The game/reduction label (used only in a leading comment).
        text: Raw LaTeX commentary text.
        out_path: Destination file path.
    """
    content = f"% TeXFrog commentary for game: {game_label}\n{text}"
    out_path.write_text(content, encoding="utf-8")


def _write_harness_file(proof: Proof, output_dir: Path, out_path: Path) -> None:
    r"""Write the proof harness LaTeX file.

    The harness:
    * Defines default ``\tfchanged`` and ``\tfgamelabel`` macros.
    * ``\input``s each macro file listed in the proof config.
    * ``\input``s each game file and commentary file in order.

    Args:
        proof: The parsed proof.
        output_dir: Directory where game/commentary files were written (used
            to produce relative paths for ``\input``).
        out_path: Destination file path for the harness.
    """
    lines: list[str] = [
        "% TeXFrog proof harness — \\input this file in your main paper\n",
        "%\n",
        "% Default highlight macro for changed lines:\n",
        r"\providecommand{\tfchanged}[1]{\colorbox{blue!15}{$#1$}}" + "\n",
        "% Default game label macro for consolidated figures:\n",
        r"\providecommand{\tfgamelabel}[2]{#2\;{\scriptsize\textit{[#1]}}}" + "\n",
        "%\n",
    ]

    # Macro files (paths relative to harness location)
    for macro_file in proof.macros:
        lines.append(f"\\input{{{macro_file}}}\n")

    lines.append("%\n")

    # Game files + commentary
    for game in proof.games:
        label = game.label
        game_file = f"{label}.tex"
        commentary_file = f"{label}_commentary.tex"

        lines.append(f"% --- {label}: {game.latex_name} ---\n")
        lines.append(f"\\input{{{game_file}}}\n")

        commentary_path = output_dir / commentary_file
        if commentary_path.exists():
            lines.append(f"\\input{{{commentary_file}}}\n")

        lines.append("%\n")

    out_path.write_text("".join(lines), encoding="utf-8")


def _write_consolidated_figure(
    proof: Proof,
    figure_label: str,
    game_labels: list[str],
    out_path: Path,
) -> None:
    r"""Write a consolidated figure showing multiple games side by side.

    For each source line:
    * If it appears in **all** selected games: output verbatim.
    * If it appears in a **subset**: wrap with ``\tfgamelabel{labels}{content}``,
      where ``labels`` is a comma-separated list of the games that include it.
    * If it appears in **none**: skip it.

    Args:
        proof: The parsed proof.
        figure_label: Internal label for the figure (used in leading comment).
        game_labels: Ordered list of game labels to include in this figure.
        out_path: Destination file path.
    """
    n = len(game_labels)

    # Build per-game filtered line sets for membership testing.
    # We use a list of frozensets of content strings for each game.
    per_game_lines: list[list[str]] = [
        filter_for_game(proof.source_lines, lbl) for lbl in game_labels
    ]

    # For the consolidated view, iterate over the UNION of all included lines
    # in their original source order.
    output_parts: list[str] = [
        f"% TeXFrog consolidated figure: {figure_label} ({', '.join(game_labels)})\n"
    ]

    # Track which source lines are included by at least one game.
    for sl in proof.source_lines:
        # Determine which of the selected games include this line.
        present_in: list[str] = []
        for label in game_labels:
            if sl.tags is None or label in sl.tags:
                present_in.append(label)

        if not present_in:
            continue  # No selected game includes this line

        if len(present_in) == n:
            # Present in ALL selected games — no annotation needed.
            output_parts.append(sl.content + "\n")
        else:
            # Present in only some games — annotate.
            label_str = ",".join(present_in)
            output_parts.append(
                f"{_GAMELABEL_MACRO}{{{label_str}}}{{{sl.content}}}\n"
            )

    out_path.write_text("".join(output_parts), encoding="utf-8")


def generate_latex(proof: Proof, output_dir: Path) -> None:
    """Generate all LaTeX output files for the proof.

    Creates:
    * ``{label}.tex`` for each game/reduction.
    * ``{label}_commentary.tex`` for each game with commentary.
    * ``proof_harness.tex`` — the main harness file.
    * ``fig_{label}.tex`` for each consolidated figure.

    Args:
        proof: The parsed proof.
        output_dir: Directory to write output files into (created if needed).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build filtered lines per game, then compute diffs.
    game_lines: dict[str, list[str]] = {}
    for game in proof.games:
        game_lines[game.label] = filter_for_game(proof.source_lines, game.label)

    ordered_labels = [g.label for g in proof.games]

    for i, game in enumerate(proof.games):
        label = game.label
        current = game_lines[label]

        # Compute changed lines relative to previous game.
        if i == 0:
            changed: set[int] = set()
        else:
            prev_label = ordered_labels[i - 1]
            changed = compute_changed_lines(game_lines[prev_label], current)

        # Write per-game file.
        _write_game_file(label, current, changed, output_dir / f"{label}.tex")

        # Write commentary file if commentary exists.
        commentary = proof.commentary.get(label, "")
        if commentary.strip():
            _write_commentary_file(
                label, commentary, output_dir / f"{label}_commentary.tex"
            )

    # Write harness.
    _write_harness_file(proof, output_dir, output_dir / "proof_harness.tex")

    # Write consolidated figures.
    for figure in proof.figures:
        _write_consolidated_figure(
            proof,
            figure.label,
            figure.games,
            output_dir / f"fig_{figure.label}.tex",
        )
