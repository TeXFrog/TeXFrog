"""Validation checks for TeXFrog proofs."""

from __future__ import annotations

from pathlib import Path

from .filter import filter_for_game
from .model import Proof
from .parser import validate_tags
from .tex_parser import filter_for_game_from_text


def validate_proof(proof: Proof, base_dir: Path) -> list[str]:
    """Run all non-fatal validation checks on a parsed proof.

    Returns a list of human-readable warning strings (may be empty).
    This consolidates tag warnings from :func:`~texfrog.parser.validate_tags`
    with additional checks for file existence, empty games, and unknown
    commentary keys.

    Args:
        proof: A fully parsed :class:`Proof` instance.
        base_dir: The directory containing the proof YAML file (used to
            resolve relative macro paths).

    Returns:
        A list of warning strings, one per issue found.
    """
    warnings: list[str] = []
    ordered_labels = [g.label for g in proof.games]

    # Tag validation (unknown tags, unused games) — YAML format only
    if proof.source_lines:
        warnings.extend(validate_tags(proof))

    # Macro file existence
    for macro_rel in proof.macros:
        macro_path = (base_dir / macro_rel).resolve()
        if not macro_path.exists():
            warnings.append(f"Macro file not found: {macro_rel}")

    # Empty games (zero lines after filtering)
    for game in proof.games:
        if proof.source_text is not None:
            lines = filter_for_game_from_text(
                proof.source_text, game.label, ordered_labels,
            )
        else:
            lines = filter_for_game(proof.source_lines, game.label)
        if not lines:
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
