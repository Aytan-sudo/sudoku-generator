"""What every output format has to provide.

The deliverable is a printed sheet, but keeping the format behind an interface
costs almost nothing and buys a text renderer for debugging — being able to see a
grid without opening a PDF viewer is worth the indirection on its own.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sudoku.generator import Puzzle


@dataclass(frozen=True, slots=True)
class Cover:
    """Front page of a booklet — what it is, and whose it is."""

    title: str
    subtitle: str = ""


class Renderer(ABC):
    """Writes a set of puzzles out in one particular format."""

    @abstractmethod
    def render(
        self,
        puzzles: Sequence[Puzzle],
        path: Path,
        *,
        solutions: bool = False,
        cover: Cover | None = None,
    ) -> None:
        """Write ``puzzles`` to ``path``, optionally with a cover and solutions."""
