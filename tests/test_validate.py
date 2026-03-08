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
