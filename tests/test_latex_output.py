"""Tests for per-game LaTeX file generation and HTML game name expansion."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.filter import compute_changed_lines
from texfrog.model import Game, Proof
from texfrog.output.html import _expand_tfgamename, _write_game_file
from texfrog.tex_parser import filter_for_game_from_text


def make_proof() -> Proof:
    """Build a small synthetic Proof for output tests."""
    games = [
        Game(label="G0", latex_name=r"\REAL()", description="Starting game."),
        Game(label="G1", latex_name="G_1", description="Modified game."),
        Game(label="G2", latex_name="G_2", description="Final game."),
    ]
    source_text = (
        r"\begin{procedure}" "\n"
        r"    common \\" "\n"
        r"\tfonly{G0}{    only_g0 \\}" "\n"
        r"\tfonly{G1,G2}{    only_g1 \\}" "\n"
        r"    \pcreturn \adv" "\n"
        r"\end{procedure}"
    )
    commentary = {
        "G0": "This is the G0 commentary.\n",
        "G1": r"\begin{claim}G0 and G1 are equiv.\end{claim}" + "\n",
    }
    return Proof(
        macros=["macros.tex"],
        games=games,
        source_text=source_text,
        commentary=commentary,
        figures=[],
    )


def _filter_game(proof: Proof, label: str) -> list[str]:
    """Filter source text for a game label."""
    ordered_labels = [g.label for g in proof.games]
    return filter_for_game_from_text(proof.source_text, label, ordered_labels)


def _write_all_game_files(proof: Proof, output_dir: Path) -> None:
    """Write per-game .tex files using the same logic as build_html_site."""
    from texfrog.packages import get_profile

    profile = get_profile(proof.package)
    proc_hdr_cmd = profile.procedure_header_cmd
    ordered_labels = [g.label for g in proof.games]

    for i, game in enumerate(proof.games):
        label = game.label
        current = filter_for_game_from_text(
            proof.source_text, label, ordered_labels,
        )

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
                    filter_for_game_from_text(
                        proof.source_text, prev_label, ordered_labels,
                    ),
                    filter_for_game_from_text(
                        proof.source_text, label, ordered_labels,
                    ),
                )

        _write_game_file(
            label, current, changed, output_dir / f"{label}.tex",
            procedure_header_cmd=proc_hdr_cmd,
        )


# ---------------------------------------------------------------------------
# Per-game files
# ---------------------------------------------------------------------------

def test_game_files_created(tmp_path):
    proof = make_proof()
    _write_all_game_files(proof, tmp_path)
    assert (tmp_path / "G0.tex").exists()
    assert (tmp_path / "G1.tex").exists()
    assert (tmp_path / "G2.tex").exists()


def test_first_game_no_tfchanged(tmp_path):
    proof = make_proof()
    _write_all_game_files(proof, tmp_path)
    text = (tmp_path / "G0.tex").read_text()
    assert r"\tfchanged" not in text


def test_changed_line_wrapped_in_g1(tmp_path):
    proof = make_proof()
    _write_all_game_files(proof, tmp_path)
    text = (tmp_path / "G1.tex").read_text()
    # "only_g1" replaces "only_g0" — should be wrapped
    assert r"\tfchanged" in text
    assert "only_g1" in text


def test_unchanged_line_not_wrapped(tmp_path):
    proof = make_proof()
    _write_all_game_files(proof, tmp_path)
    text = (tmp_path / "G1.tex").read_text()
    # "common" is unchanged; it should appear unwrapped
    assert "common" in text
    # The common line should not be inside \tfchanged
    lines_with_common = [l for l in text.splitlines() if "common" in l]
    for l in lines_with_common:
        assert r"\tfchanged" not in l


def test_write_game_file_custom_macro(tmp_path):
    """_write_game_file should use the provided macro for wrapping."""
    lines = [r"    common \\", r"    changed \\", r"    end"]
    _write_game_file("test", lines, {1}, tmp_path / "test.tex", macro=r"\tfremoved")
    text = (tmp_path / "test.tex").read_text()
    assert r"\tfremoved" in text
    assert r"\tfchanged" not in text
    assert "changed" in text


def test_excluded_line_not_in_game_file(tmp_path):
    proof = make_proof()
    _write_all_game_files(proof, tmp_path)
    g0_text = (tmp_path / "G0.tex").read_text()
    assert "only_g0" in g0_text
    assert "only_g1" not in g0_text

    g1_text = (tmp_path / "G1.tex").read_text()
    assert "only_g1" in g1_text
    assert "only_g0" not in g1_text


# ---------------------------------------------------------------------------
# Changed-line diffing skips reductions
# ---------------------------------------------------------------------------


def test_game_after_reduction_diffs_against_previous_game(tmp_path):
    """A non-reduction game should diff against the previous non-reduction game,
    not against an intervening reduction."""
    games = [
        Game(label="G0", latex_name="G_0", description=""),
        Game(label="Red", latex_name="Red", description="", reduction=True),
        Game(label="G1", latex_name="G_1", description=""),
    ]
    source_text = (
        r"    common \\" "\n"
        r"\tfonly{G0,G1}{    same_line \\}" "\n"
        r"\tfonly{Red}{    red_line \\}"
    )
    proof = Proof(
        macros=[], games=games, source_text=source_text,
        commentary={}, figures=[],
    )
    _write_all_game_files(proof, tmp_path)
    g1_text = (tmp_path / "G1.tex").read_text()
    # same_line is identical in G0 and G1, so it should NOT be highlighted
    same_lines = [l for l in g1_text.splitlines() if "same_line" in l]
    assert same_lines
    for l in same_lines:
        assert r"\tfchanged" not in l, (
            "same_line should not be marked changed when diffing G1 against G0"
        )


def test_reduction_diffs_against_immediately_preceding(tmp_path):
    """A reduction should diff against the immediately preceding entry."""
    games = [
        Game(label="G0", latex_name="G_0", description=""),
        Game(label="Red", latex_name="Red", description="", reduction=True),
    ]
    source_text = (
        r"    common \\" "\n"
        r"\tfonly{G0}{    g0_only \\}" "\n"
        r"\tfonly{Red}{    red_only \\}"
    )
    proof = Proof(
        macros=[], games=games, source_text=source_text,
        commentary={}, figures=[],
    )
    _write_all_game_files(proof, tmp_path)
    red_text = (tmp_path / "Red.tex").read_text()
    # red_only replaces g0_only — should be highlighted
    red_lines = [l for l in red_text.splitlines() if "red_only" in l]
    assert red_lines
    assert any(r"\tfchanged" in l for l in red_lines)


# ---------------------------------------------------------------------------
# Nicodemus package support
# ---------------------------------------------------------------------------


def test_nicodemus_game_item_prefix_outside_tfchanged(tmp_path):
    r"""\item prefix must stay outside \tfchanged in per-game output."""
    games = [
        Game(label="G0", latex_name="G_0", description=""),
        Game(label="G1", latex_name="G_1", description=""),
    ]
    source_text = (
        "\t\t\\begin{nicodemus}\n"
        "\t\t\t\\item common line\n"
        r"\tfonly{G0}{			\item $x\getsr\Zp$}" "\n"
        r"\tfonly{G1}{			\item $x\gets\Ogen$}" "\n"
        "\t\t\t\\item Return $x$\n"
        "\t\t\\end{nicodemus}%"
    )
    proof = Proof(
        macros=[], games=games, source_text=source_text,
        commentary={}, figures=[], package="nicodemus",
    )
    _write_all_game_files(proof, tmp_path)
    text = (tmp_path / "G1.tex").read_text()
    # G1 should have \tfchanged for the G1-only line
    assert r"\tfchanged" in text
    # \item should NOT be inside \tfchanged
    changed_lines = [l for l in text.splitlines() if r"\tfchanged" in l]
    for l in changed_lines:
        assert r"\tfchanged{\item" not in l.replace(" ", "").replace("\t", "")


# ---------------------------------------------------------------------------
# HTML game name expansion
# ---------------------------------------------------------------------------

def test_expand_tfgamename_replaces_known_labels():
    names = {"G0": r"\REAL()", "G1": "G_1"}
    text = r"In \tfgamename{G0}, we start. Then \tfgamename{G1} modifies."
    result = _expand_tfgamename(text, names)
    assert result == r"In $\REAL()$, we start. Then $G_1$ modifies."


def test_expand_tfgamename_preserves_unknown_labels():
    names = {"G0": r"\REAL()"}
    text = r"See \tfgamename{G99} for details."
    result = _expand_tfgamename(text, names)
    assert result == r"See \tfgamename{G99} for details."


def test_expand_tfgamename_no_op_without_macro():
    names = {"G0": r"\REAL()"}
    text = "No macro references here."
    result = _expand_tfgamename(text, names)
    assert result == text


def test_expand_tfgamename_inside_dollar_math():
    r"""Don't double-wrap when \tfgamename is already inside $...$."""
    names = {"G0": "G_0"}
    text = r"The starting game is $\tfgamename{G0} = \mathrm{Real}$."
    result = _expand_tfgamename(text, names)
    assert result == r"The starting game is $G_0 = \mathrm{Real}$."


def test_expand_tfgamename_mixed_math_and_text():
    """Handle both in-math and text-mode occurrences in the same string."""
    names = {"G0": "G_0", "G1": "G_1"}
    text = r"Game $\tfgamename{G0}$ equals \tfgamename{G1}."
    result = _expand_tfgamename(text, names)
    assert result == r"Game $G_0$ equals $G_1$."


def test_expand_tfgamename_inside_paren_math():
    r"""Don't double-wrap when \tfgamename is inside \(...\)."""
    names = {"G0": "G_0"}
    text = r"See \(\tfgamename{G0} = X\) for details."
    result = _expand_tfgamename(text, names)
    assert result == r"See \(G_0 = X\) for details."


def test_expand_tfgamename_inside_bracket_math():
    r"""Don't double-wrap when \tfgamename is inside \[...\]."""
    names = {"G0": "G_0"}
    text = r"Display: \[\tfgamename{G0} = X\]"
    result = _expand_tfgamename(text, names)
    assert result == r"Display: \[G_0 = X\]"


def test_expand_tfgamename_comment_with_dollar():
    r"""A $ inside a LaTeX comment should not affect math-mode tracking."""
    names = {"G0": "G_0"}
    text = "Some text % comment with a $\n\\tfgamename{G0} here."
    result = _expand_tfgamename(text, names)
    assert result == "Some text % comment with a $\n$G_0$ here."


# ---------------------------------------------------------------------------
# _pdfcrop warning on failure
# ---------------------------------------------------------------------------


def test_pdfcrop_failure_emits_warning(tmp_path, capsys):
    """When pdfcrop returns non-zero, a warning should be printed to stderr."""
    from unittest.mock import patch, MagicMock

    from texfrog.output.html import _pdfcrop

    pdf = tmp_path / "test.pdf"
    pdf.write_text("fake pdf")

    mock_result = MagicMock()
    mock_result.returncode = 1

    with patch("shutil.which", return_value="/usr/bin/pdfcrop"), \
         patch("subprocess.run", return_value=mock_result):
        result = _pdfcrop(pdf)

    assert result == pdf  # falls back to original
    captured = capsys.readouterr()
    assert "pdfcrop failed" in captured.err
    assert "test.pdf" in captured.err
