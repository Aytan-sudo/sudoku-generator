"""What every output format has to provide.

The deliverable is a printed sheet, but keeping the format behind an interface
costs almost nothing and buys a text renderer for debugging — being able to see a
grid without opening a PDF viewer is worth the indirection on its own.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from sudoku.generator import Puzzle


class Renderer(ABC):
    """Writes a set of puzzles out in one particular format."""

    @abstractmethod
    def render(self, puzzles: Sequence[Puzzle], path: Path, *, solutions: bool = False) -> None:
        """Write ``puzzles`` to ``path``, optionally followed by their solutions."""
