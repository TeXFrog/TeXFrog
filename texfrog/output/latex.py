"""LaTeX output generators for TeXFrog."""

from __future__ import annotations

from pathlib import Path

from ..filter import compute_changed_lines, filter_for_game, wrap_changed_line
from ..model import Proof
from ..packages import get_profile

# Macro used to highlight changed lines.
_CHANGED_MACRO = r"\tfchanged"

# Macro used to annotate game-specific lines in consolidated figures.
_GAMELABEL_MACRO = r"\tfgamelabel"


def _write_game_file(
    game_label: str,
    current_lines: list[str],
    changed_indices: set[int],
    out_path: Path,
    macro: str = _CHANGED_MACRO,
    procedure_header_cmd: str | None = None,
) -> None:
    """Write per-game LaTeX file with changed lines highlighted.

    Args:
        game_label: The game/reduction label (used only in a leading comment).
        current_lines: Filtered content lines for this game.
        changed_indices: 0-based indices of lines to wrap with a highlighting macro.
        out_path: Destination file path.
        macro: LaTeX macro name to use for wrapping (default ``\\tfchanged``).
        procedure_header_cmd: Package-specific command name (without backslash)
            for procedure headers that should never be wrapped.
    """
    parts: list[str] = [f"% TeXFrog output for game: {game_label}\n"]
    for i, line in enumerate(current_lines):
        # Skip blank lines — they arise from excluded tagged content and can
        # cause LaTeX dimension errors inside pseudocode environments
        # (e.g. varwidth used internally by cryptocode's pcvstack).
        if not line.strip():
            continue
        if i in changed_indices:
            parts.append(
                wrap_changed_line(line, macro, procedure_header_cmd) + "\n"
            )
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


def _write_sty_file(proof: Proof, out_path: Path) -> None:
    r"""Write the ``texfrog.sty`` package file.

    The package defines:
    * ``\tfchanged`` — highlighting macro for changed lines.
    * ``\tfgamelabel`` — annotation macro for consolidated figures.
    * ``\tfgamename`` — game name lookup dispatcher.
    * Any package-specific extras (e.g. ``\nicodemusheader``).

    Args:
        proof: The parsed proof.
        out_path: Destination file path for the ``.sty`` file.
    """
    profile = get_profile(proof.package)
    lines: list[str] = [
        r"\NeedsTeXFormat{LaTeX2e}" + "\n",
        r"\ProvidesPackage{texfrog}[TeXFrog proof macros]" + "\n",
        "%\n",
        "% Highlight macro for changed lines:\n",
        profile.harness_tfchanged() + "\n",
        "% Game label macro for consolidated figures:\n",
        profile.harness_tfgamelabel() + "\n",
    ]
    proc_hdr_def = profile.procedure_header_def()
    if proc_hdr_def:
        lines += [
            "% Procedure header command:\n",
            proc_hdr_def + "\n",
        ]
    lines += [
        "%\n",
        "% Game name lookup macro (use \\tfgamename{label} in your paper):\n",
        r"\makeatletter" + "\n",
        r"\providecommand{\tfgamename}[1]{\ensuremath{\@nameuse{tfgn@#1}}}" + "\n",
    ]
    for game in proof.games:
        lines.append(f"\\@namedef{{tfgn@{game.label}}}{{{game.latex_name}}}\n")
    lines += [
        r"\makeatother" + "\n",
    ]
    out_path.write_text("".join(lines), encoding="utf-8")


def _write_harness_file(proof: Proof, output_dir: Path, out_path: Path) -> None:
    r"""Write the proof harness LaTeX file.

    The harness ``\input``s each game file and commentary file in order.
    Macro definitions live in ``texfrog.sty`` (loaded via
    ``\usepackage{texfrog}`` in the paper preamble).

    Args:
        proof: The parsed proof.
        output_dir: Directory where game/commentary files were written (used
            to produce relative paths for ``\input``).
        out_path: Destination file path for the harness.
    """
    lines: list[str] = [
        "% TeXFrog proof harness — \\input this file in your main paper\n",
        "% (load \\usepackage{texfrog} in your preamble first)\n",
        "%\n",
    ]

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
    profile = get_profile(proof.package)
    proc_hdr_cmd = profile.procedure_header_cmd
    n = len(game_labels)

    # For the consolidated view, iterate over the UNION of all included lines
    # in their original source order.
    output_parts: list[str] = [
        f"% TeXFrog consolidated figure: {figure_label} ({', '.join(game_labels)})\n"
    ]

    # Procedure headers (lines ending with "{", or starting with the
    # package-specific header command) require special handling: a
    # \procedure environment can only be opened once, so consecutive game-specific
    # header variants must collapse to a single line.  We track whether the
    # previous emitted-or-skipped line was a procedure header; when it was, any
    # further procedure-header variant is silently dropped.
    last_was_proc_header = False

    for sl in proof.source_lines:
        # Determine which of the selected games include this line.
        present_in: list[str] = []
        for label in game_labels:
            if sl.tags is None or label in sl.tags:
                present_in.append(label)

        if not present_in:
            continue  # No selected game includes this line

        # Skip blank lines — same reason as _write_game_file: varwidth inside
        # pcvstack chokes on blank lines and raises "Dimension too large".
        if not sl.content.strip():
            continue

        trimmed_content = sl.content.strip()
        is_proc_header = sl.content.rstrip().endswith("{")
        if proc_hdr_cmd and trimmed_content.startswith(f"\\{proc_hdr_cmd}{{"):
            is_proc_header = True

        if is_proc_header and last_was_proc_header:
            # Subsequent variant in a procedure-header slot — skip it so that
            # only one \procedure command appears in the consolidated output.
            continue

        last_was_proc_header = is_proc_header

        if len(present_in) == n or is_proc_header:
            # Present in ALL selected games, or is a procedure header that must
            # not be annotated — output verbatim.
            output_parts.append(sl.content + "\n")
        else:
            # Present in only some games — annotate.
            # Build a partial macro including the label arg so that
            # wrap_changed_line can place any trailing \\ *outside* the braces.
            label_str = ",".join(
                rf"\tfgamename{{{lbl}}}" for lbl in present_in
            )
            partial_macro = f"{_GAMELABEL_MACRO}{{{label_str}}}"
            output_parts.append(
                wrap_changed_line(sl.content, partial_macro, proc_hdr_cmd) + "\n"
            )

    # Post-processing: insert \\ between consecutive procedure-body lines that
    # lack one.  This can happen when multiple game-variant "last lines" (which
    # have no \\ in the source, since they end their respective game's body)
    # all appear together in the consolidated output.
    # Only applies to packages that use \\ as a line separator (e.g. cryptocode).
    if profile.has_line_separators:
        final_parts: list[str] = []
        for i, raw in enumerate(output_parts):
            line = raw.rstrip("\n")
            stripped = line.strip()

            # Only consider adding \\ to lines that are pseudocode content:
            # not empty, not a comment, not a structural brace/environment line,
            # and not already ending with \\.
            if (
                stripped
                and not stripped.startswith("%")
                and stripped != "}"
                and not stripped.startswith("\\begin{")
                and not stripped.startswith("\\end{")
                and not line.rstrip().endswith("{")
                and not line.rstrip().endswith("\\\\")
            ):
                # Look ahead to the next non-comment content line.
                for j in range(i + 1, len(output_parts)):
                    nc = output_parts[j].strip()
                    if nc and not nc.startswith("%"):
                        if nc != "}" and not nc.startswith("\\end{"):
                            line = line.rstrip() + " \\\\"
                        break

            final_parts.append(line + "\n")
    else:
        final_parts = output_parts

    out_path.write_text("".join(final_parts), encoding="utf-8")


def generate_latex(proof: Proof, output_dir: Path) -> None:
    """Generate all LaTeX output files for the proof.

    Creates:
    * ``texfrog.sty`` — package with macro definitions.
    * ``{label}.tex`` for each game/reduction.
    * ``{label}_commentary.tex`` for each game with commentary.
    * ``proof_harness.tex`` — inputs game and commentary files in order.
    * ``fig_{label}.tex`` for each consolidated figure.

    Args:
        proof: The parsed proof.
        output_dir: Directory to write output files into (created if needed).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    profile = get_profile(proof.package)
    proc_hdr_cmd = profile.procedure_header_cmd

    # Build filtered lines per game, then compute diffs.
    game_lines: dict[str, list[str]] = {}
    for game in proof.games:
        game_lines[game.label] = filter_for_game(proof.source_lines, game.label)

    ordered_labels = [g.label for g in proof.games]

    for i, game in enumerate(proof.games):
        label = game.label
        current = game_lines[label]

        # Compute changed lines relative to previous game.
        # Non-reduction games diff against the previous non-reduction game
        # (skipping intervening reductions); reductions diff against the
        # immediately preceding entry.
        if i == 0:
            changed: set[int] = set()
        else:
            if game.reduction:
                prev_label = ordered_labels[i - 1]
            else:
                prev_label = None
                for j in range(i - 1, -1, -1):
                    if not proof.games[j].reduction:
                        prev_label = ordered_labels[j]
                        break
            if prev_label is None:
                changed = set()
            else:
                changed = compute_changed_lines(
                    game_lines[prev_label], current
                )

        # Write per-game file.
        _write_game_file(
            label, current, changed, output_dir / f"{label}.tex",
            procedure_header_cmd=proc_hdr_cmd,
        )

        # Write commentary file if commentary exists.
        commentary = proof.commentary.get(label, "")
        if commentary.strip():
            _write_commentary_file(
                label, commentary, output_dir / f"{label}_commentary.tex"
            )

    # Write texfrog.sty.
    _write_sty_file(proof, output_dir / "texfrog.sty")

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
