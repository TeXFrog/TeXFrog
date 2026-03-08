"""Data models for TeXFrog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Game:
    """A single game or reduction in the proof sequence."""
    label: str        # Internal label, e.g. "G0", "Red2"
    latex_name: str   # Math-mode LaTeX for the name (no $ delimiters), e.g. r'\indcca_\QSH^\adv.\REAL()'
    description: str  # One-sentence LaTeX description
    reduction: bool = False  # True for reductions (shown alone, not side-by-side)
    related_games: list[str] = field(default_factory=list)  # 0–2 game labels shown alongside this reduction


@dataclass
class Figure:
    """A consolidated figure showing several games side by side."""
    label: str         # Internal label, e.g. "fig_start_end"
    games: list[str]   # Ordered list of game labels to include
    procedure_name: Optional[str] = None  # Custom title for the first procedure header


@dataclass
class Proof:
    """The top-level proof object, parsed from a .tex input file."""
    macros: list[str]               # Paths to macro .tex files (relative to input dir)
    games: list[Game]               # All games/reductions in order
    source_text: str                # Raw tfsource body (\tfonly format)
    commentary: dict[str, str]      # game_label -> LaTeX commentary text (loaded from files)
    figures: list[Figure]           # Consolidated figure specs
    package: str = "cryptocode"     # Package profile name (see packages.py)
    preamble: Optional[str] = None  # Path to extra preamble .tex file (relative to input dir)
    commentary_files: dict[str, str] = field(default_factory=dict)  # game_label -> relative file path
