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
        player: str | None = None,
    ) -> None:
        """Write ``puzzles`` to ``path``, optionally with a cover and solutions.

        ``player`` fills in the name that would otherwise be left blank — worth
        it when a booklet is meant for someone in particular, rather than making
        them write their name twenty times.
        """

    @abstractmethod
    def render_solutions(
        self,
        puzzles: Sequence[Puzzle],
        path: Path,
        *,
        cover: Cover | None = None,
    ) -> None:
        """Write only the solutions, as a document of their own.

        Keeping them apart is what lets the booklet be handed over while the
        answers stay with whoever is checking.
        """
