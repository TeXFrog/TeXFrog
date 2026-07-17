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

    # Segment warnings for cropping feature
    from .filter import SEGMENT_RE

    src_lines = proof.source_text.split("\n")
    seg_count = 0
    depth = 0
    _OPENERS = (r"\If", r"\For", r"\While")
    _CLOSERS = (r"\EndIf", r"\EndFor", r"\EndWhile")
    for ln in src_lines:
        stripped = ln.strip()
        m = SEGMENT_RE.match(ln)
        if m:
            seg_count += 1
            if not m.group("caption").strip():
                warnings.append(
                    f"{proof.source_name}: \\tfsegment has an empty caption."
                )
            if depth != 0:
                warnings.append(
                    f"{proof.source_name}: \\tfsegment{{{m.group('caption')}}} "
                    f"is at block depth {depth} (inside \\If/\\For/\\While); "
                    "segments must start at depth 0 to crop safely."
                )
        # crude block-depth tracking for algpseudocodex-style bodies
        for closer in _CLOSERS:
            if stripped.startswith(closer):
                depth = max(0, depth - 1)
        for opener in _OPENERS:
            if stripped.startswith(opener):
                depth += 1
    if proof.crop_default and seg_count == 0:
        warnings.append(
            f"{proof.source_name}: \\tfcropdefault is on but the source has no "
            "\\tfsegment markers, so cropping cannot shrink the listing."
        )

    return warnings
