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
class SourceLine:
    """A single physical line from the combined source file."""
    content: str                    # Line content with tag comment stripped
    tags: Optional[frozenset[str]]  # None means "all games"; set means specific labels
    original: str                   # Original raw line (for debugging)


@dataclass
class Figure:
    """A consolidated figure showing several games side by side."""
    label: str         # Internal label, e.g. "fig_start_end"
    games: list[str]   # Ordered list of game labels to include
    procedure_name: Optional[str] = None  # Custom title for the first procedure header


@dataclass
class Proof:
    """The top-level proof object, parsed from the YAML input."""
    macros: list[str]               # Paths to macro .tex files (relative to yaml dir)
    games: list[Game]               # All games/reductions in order
    source_lines: list[SourceLine]  # Combined source lines
    commentary: dict[str, str]      # game_label -> LaTeX commentary text
    figures: list[Figure]           # Consolidated figure specs
    package: str = "cryptocode"     # Package profile name (see packages.py)
    preamble: Optional[str] = None  # Path to extra preamble .tex file (relative to yaml dir)
