"""Validation checks for TeXFrog proofs."""

from __future__ import annotations

from pathlib import Path

from .model import Proof
from .tex_parser import filter_for_game_from_text


def validate_proof(proof: Proof, base_dir: Path) -> list[str]:
    """Run all non-fatal validation checks on a parsed proof.

    Returns a list of human-readable warning strings (may be empty).
    Checks for file existence, empty games, and unknown commentary keys.

    Args:
        proof: A fully parsed :class:`Proof` instance.
        base_dir: The directory containing the proof .tex file (used to
            resolve relative macro paths).

    Returns:
        A list of warning strings, one per issue found.
    """
    warnings: list[str] = []
    ordered_labels = [g.label for g in proof.games]

    # Macro file existence
    for macro_rel in proof.macros:
        macro_path = (base_dir / macro_rel).resolve()
        if not macro_path.exists():
            warnings.append(f"Macro file not found: {macro_rel}")

    # Empty games (zero lines after filtering)
    for game in proof.games:
        lines = filter_for_game_from_text(
            proof.source_text, game.label, ordered_labels,
        )
        if not any(line.strip() for line in lines):
            warnings.append(
                f"Game '{game.label}' produces an empty game "
                f"(0 lines after filtering)."
            )

    # Unknown commentary keys
    defined_labels = {g.label for g in proof.games}
    for key in proof.commentary:
        if key not in defined_labels:
            warnings.append(
                f"Commentary key '{key}' does not match any game label."
            )

    return warnings
