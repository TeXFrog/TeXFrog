"""Tests for texfrog.validate."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.model import Figure, Game, Proof
from texfrog.validate import validate_proof


def _make_proof(
    *,
    games=None,
    source_text=None,
    macros=None,
    commentary=None,
    figures=None,
    package="cryptocode",
    preamble=None,
) -> Proof:
    """Helper to create a Proof with sensible defaults."""
    if games is None:
        games = [
            Game(label="G0", latex_name="G_0", description="Game 0",
                 reduction=False, related_games=[]),
            Game(label="G1", latex_name="G_1", description="Game 1",
                 reduction=False, related_games=[]),
        ]
    if source_text is None:
        source_text = (
            "common line\n"
            r"\tfonly{G0}{only G0}" "\n"
            r"\tfonly{G1}{only G1}"
        )
    return Proof(
        source_name="main",
        macros=macros or [],
        games=games,
        source_text=source_text,
        commentary=commentary or {},
        figures=figures or [],
        package=package,
        preamble=preamble,
    )


class TestValidateProof:
    """Tests for validate_proof()."""

    def test_clean_proof(self, tmp_path):
        """A well-formed proof should produce no warnings."""
        proof = _make_proof()
        warnings = validate_proof(proof, tmp_path)
        assert warnings == []

    def test_macro_file_missing(self, tmp_path):
        """Missing macro file should produce a warning."""
        proof = _make_proof(macros=["nonexistent.tex"])
        warnings = validate_proof(proof, tmp_path)
        assert any("nonexistent.tex" in w for w in warnings)

    def test_macro_file_exists(self, tmp_path):
        """Existing macro file should not produce a warning."""
        (tmp_path / "macros.tex").write_text("% macros", encoding="utf-8")
        proof = _make_proof(macros=["macros.tex"])
        warnings = validate_proof(proof, tmp_path)
        assert not any("macros.tex" in w for w in warnings)

    def test_empty_game(self, tmp_path):
        """A game with no lines after filtering should produce a warning."""
        games = [
            Game(label="G0", latex_name="G_0", description="Game 0",
                 reduction=False, related_games=[]),
            Game(label="G1", latex_name="G_1", description="Game 1",
                 reduction=False, related_games=[]),
        ]
        # All tagged content is for G0 only — G1 gets nothing
        source_text = r"\tfonly{G0}{tagged for G0}"
        proof = _make_proof(games=games, source_text=source_text)
        warnings = validate_proof(proof, tmp_path)
        assert any("G1" in w and "empty" in w for w in warnings)

    def test_non_empty_games(self, tmp_path):
        """Games with lines should not trigger an empty warning."""
        proof = _make_proof()
        warnings = validate_proof(proof, tmp_path)
        assert not any("empty" in w for w in warnings)

    def test_unknown_commentary_key(self, tmp_path):
        """Commentary key not matching any game should produce a warning."""
        proof = _make_proof(commentary={"G0": "text", "G99": "orphan"})
        warnings = validate_proof(proof, tmp_path)
        assert any("G99" in w and "commentary" in w.lower() for w in warnings)

    def test_valid_commentary_keys(self, tmp_path):
        """Commentary keys matching game labels should not warn."""
        proof = _make_proof(commentary={"G0": "text", "G1": "text"})
        warnings = validate_proof(proof, tmp_path)
        assert not any("commentary" in w.lower() for w in warnings)

    def test_multiple_warnings_combined(self, tmp_path):
        """Multiple issues should each produce a warning."""
        source_text = r"\tfonly{G0}{only G0}"
        proof = _make_proof(
            source_text=source_text,
            macros=["missing.tex"],
            commentary={"G99": "orphan"},
        )
        warnings = validate_proof(proof, tmp_path)
        # Should have: empty game G1, missing macro, unknown commentary
        assert len(warnings) >= 3

    def test_warns_empty_segment_caption(self, minimal_proof_factory, tmp_path):
        """\\tfsegment with empty caption should produce a warning."""
        proof = minimal_proof_factory(source_text="\\State a\n\\tfsegment{}\n\\State b\n")
        warnings = validate_proof(proof, tmp_path)
        assert any("empty" in w.lower() and "tfsegment" in w for w in warnings)

    def test_warns_segment_inside_if(self, minimal_proof_factory, tmp_path):
        """\\tfsegment inside \\If block should produce a warning."""
        src = "\\If{c}\n\\tfsegment{Bad}\n\\EndIf\n"
        proof = minimal_proof_factory(source_text=src)
        warnings = validate_proof(proof, tmp_path)
        assert any("depth" in w.lower() or "inside" in w.lower() for w in warnings)

    @pytest.mark.parametrize(
        "opener,closer",
        [
            (r"\Function{Foo}{x}", r"\EndFunction"),
            (r"\Procedure{Foo}{x}", r"\EndProcedure"),
            (r"\Loop", r"\EndLoop"),
            (r"\Repeat", r"\Until{c}"),
        ],
    )
    def test_warns_segment_inside_block(
        self, minimal_proof_factory, tmp_path, opener, closer
    ):
        """\\tfsegment inside a \\Function/\\Procedure/\\Loop/\\Repeat block
        must warn like \\If -- cropping can drop the opener while keeping the
        closer, unbalancing the block."""
        src = f"{opener}\n\\State a\n\\tfsegment{{Bad}}\n\\State b\n{closer}\n"
        proof = minimal_proof_factory(source_text=src)
        warnings = validate_proof(proof, tmp_path)
        assert any("depth" in w.lower() for w in warnings), warnings

    def test_no_depth_warning_for_forall_double_count(
        self, minimal_proof_factory, tmp_path
    ):
        """A \\ForAll ... \\EndFor block returns to depth 0 (it is counted
        once, via the \\For opener prefix, not twice), so a \\tfsegment placed
        after the block closes is NOT flagged."""
        src = "\\ForAll{x}\n\\State a\n\\EndFor\n\\tfsegment{OK}\n\\State b\n"
        proof = minimal_proof_factory(source_text=src)
        warnings = validate_proof(proof, tmp_path)
        assert not any("depth" in w.lower() for w in warnings), warnings

    def test_warns_crop_without_segments(self, minimal_proof_factory, tmp_path):
        """\\tfcropdefault on but no \\tfsegment markers should warn."""
        proof = minimal_proof_factory(source_text="\\State a\n", crop_default=True)
        warnings = validate_proof(proof, tmp_path)
        assert any("no" in w.lower() and "tfsegment" in w for w in warnings)

    def test_warns_segment_with_brace_caption(self, minimal_proof_factory, tmp_path):
        """A \\tfsegment caption containing braces should produce a warning.

        \\tfsegment{Setup \\textbf{one}} is accepted by the LaTeX
        NewDocumentCommand (balanced-brace grab), but SEGMENT_RE's
        ``[^{}]*`` charset does not match it, so it would otherwise be
        silently missed by the split/crop machinery.
        """
        src = "\\State a\n\\tfsegment{Setup \\textbf{one}}\n\\State b\n"
        proof = minimal_proof_factory(source_text=src)
        warnings = validate_proof(proof, tmp_path)
        assert any("tfsegment" in w for w in warnings)

    def test_warns_segment_sharing_line(self, minimal_proof_factory, tmp_path):
        """A \\tfsegment marker sharing a line with other content should warn."""
        src = "\\State a\n\\State b \\tfsegment{Mid}\n\\State c\n"
        proof = minimal_proof_factory(source_text=src)
        warnings = validate_proof(proof, tmp_path)
        assert any("tfsegment" in w for w in warnings)

    def test_no_malformed_warning_for_plain_marker(
        self, minimal_proof_factory, tmp_path
    ):
        """A well-formed, standalone \\tfsegment marker should not trigger
        the malformed-marker warning (only the well-formed-marker checks
        apply)."""
        src = "\\State a\n\\tfsegment{Setup}\n\\State b\n"
        proof = minimal_proof_factory(source_text=src)
        warnings = validate_proof(proof, tmp_path)
        assert not any("not a plain marker" in w for w in warnings)

    def test_no_malformed_warning_for_tfsegmentstub(
        self, minimal_proof_factory, tmp_path
    ):
        """\\tfsegmentstub (a distinct, longer command) must not be mistaken
        for a malformed \\tfsegment marker."""
        src = "\\State a\n\\tfsegmentstub{Setup}\n\\State b\n"
        proof = minimal_proof_factory(source_text=src)
        warnings = validate_proof(proof, tmp_path)
        assert not any("not a plain marker" in w for w in warnings)
