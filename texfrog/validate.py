"""Validation checks for TeXFrog proofs."""

from __future__ import annotations

import re
from pathlib import Path

from .filter import SEGMENT_RE
from .model import Proof
from .tex_parser import filter_for_game_from_text

# Detects any occurrence of the \tfsegment control word (but not the longer
# \tfsegmentstub, thanks to the trailing \b) so we can flag lines that
# contain a marker SEGMENT_RE doesn't recognise: e.g. a brace-containing
# caption (\tfsegment{Setup \textbf{one}}), a marker sharing a line with
# other content, or a marker nested inside a \tfonly{...} body. SEGMENT_RE's
# ``[^{}]*`` caption charset (shared with the LaTeX-side scan regex) accepts
# none of these, so without this check they would silently misalign the
# split and cause a cryptic downstream compile failure.
_TFSEGMENT_OCCURRENCE_RE = re.compile(r"\\tfsegment\b")


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

    # Segment warnings for cropping feature.
    # Block-depth tracking covers the algpseudocodex block commands whose
    # opener and closer can straddle a \tfsegment boundary: \If/\For/\While,
    # plus \Function/\Procedure/\Loop/\Repeat. A marker nested inside any of
    # these sits at nonzero depth, so cropping could drop the opener while
    # keeping the closer (or vice versa) and produce an unbalanced block --
    # the same failure class for all of them (unlike cryptocode's distinct
    # brace-group split failure). \ForAll is caught by the \For prefix and
    # is deliberately not listed separately, so a \ForAll line is not counted
    # twice.
    src_lines = proof.source_text.split("\n")
    seg_count = 0
    depth = 0
    _OPENERS = (
        r"\If", r"\For", r"\While",
        r"\Function", r"\Procedure", r"\Loop", r"\Repeat",
    )
    _CLOSERS = (
        r"\EndIf", r"\EndFor", r"\EndWhile",
        r"\EndFunction", r"\EndProcedure", r"\EndLoop", r"\Until",
    )
    for ln in src_lines:
        stripped = ln.strip()
        m = SEGMENT_RE.match(ln)
        if m:
            seg_count += 1
            if not m.group("caption").strip():
                warnings.append(
                    f"{proof.source_name}: \\tfsegment #{seg_count} has an "
                    "empty caption."
                )
            if depth != 0:
                warnings.append(
                    f"{proof.source_name}: \\tfsegment{{{m.group('caption')}}} "
                    f"is at block depth {depth} (inside a block such as "
                    "\\If/\\For/\\While/\\Function/\\Procedure/\\Loop/\\Repeat); "
                    "segments must start at depth 0 to crop safely."
                )
        elif _TFSEGMENT_OCCURRENCE_RE.search(ln):
            # Contains \tfsegment but doesn't match the plain-marker form:
            # brace-containing caption, marker not alone on its own line, or
            # marker nested inside a \tfonly{...} body. Any of these would
            # be invisible to the split regex and produce a silent
            # segment/body misalignment rather than a caught error.
            warnings.append(
                f"{proof.source_name}: line contains \\tfsegment but is not "
                "a plain marker of the form '\\tfsegment{caption}' alone on "
                "its own line: "
                f"{stripped!r}. Segment captions must not contain braces, "
                "and the marker must not share a line with other content "
                "or sit inside a \\tfonly{...} body."
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
