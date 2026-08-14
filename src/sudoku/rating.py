"""Turning a solve log into a level from 1 to 10.

The thresholds here are measured, not guessed. ``tools/calibrate.py`` dug 4000
grids across the 22-58 givens range and reported what actually varies with
difficulty; two of the three metrics originally planned for this module did not
survive that sample:

* The **bottleneck** — the fewest moves offered at any single point of a solve —
  is 1 on virtually every grid, easy ones included. There is almost always a
  moment where only one move is on the table. Discarded.
* The **technique ceiling** saturates. "Hidden single in a box" is the ceiling of
  grids from 22 to 58 givens, so it cannot separate the lower levels. It is kept,
  but only to impose a *floor*: a grid that forces a harder technique cannot be
  rated easy, however open it otherwise looks.

What did survive is **visibility**: the mean share of the still-empty cells that
were immediately placeable at each step. It falls cleanly from 48% at 54 givens
to 12% at 23, and — the part that matters — it still spreads by a factor of two
between quartiles at a *fixed* given count. That spread is the difference between
two grids that look alike on paper and feel nothing alike to solve.

So the rating is: a level read off visibility, then raised if the technique
ceiling demands it.

Levels 7 to 10 rest on thinner ground for now. The techniques that define them do
not exist yet (step 7 of ROADMAP.md), so grids needing them all land in the same
"beyond the catalogue" bucket. Their thresholds are placeholders to be
re-measured once that step lands; levels 1 to 6 are the ones the sample actually
pins down.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from sudoku.board import Board
from sudoku.human import SolveLog, solve_logically
from sudoku.techniques import CATALOGUE, Technique

__all__ = ["LEVELS", "Level", "Rating", "level_of", "rate", "visibility_of"]


@dataclass(frozen=True, slots=True)
class Level:
    """One rung of the ten-level scale."""

    number: int
    name: str
    min_visibility: float
    """Lowest visibility that still counts as this level."""


LEVELS: tuple[Level, ...] = (
    Level(1, "Découverte", 0.42),
    Level(2, "Premiers pas", 0.36),
    Level(3, "Facile", 0.30),
    Level(4, "Facile +", 0.25),
    Level(5, "Moyen", 0.21),
    Level(6, "Moyen +", 0.18),
    Level(7, "Confirmé", 0.16),
    Level(8, "Difficile", 0.14),
    Level(9, "Expert", 0.0),
    Level(10, "Diabolique", 0.0),
)
"""The scale, easiest first. Thresholds come from the medians measured per given
count: 0.46 at 54 givens, 0.35 at 44, 0.26 at 38, 0.21 at 34, 0.17 at 30."""

BY_NUMBER: dict[int, Level] = {level.number: level for level in LEVELS}

BEYOND_LEVEL = 10
"""Reached when the catalogue runs out before the grid does."""

CEILING_FLOOR: dict[str, int] = {
    "full_house": 1,
    "hidden_single_box": 1,
    "hidden_single_line": 5,
    "naked_single": 6,
}
"""Lowest level a grid may be rated, given the hardest technique it forced.

Extended alongside the catalogue: step 7 adds locked candidates at 7, pairs and
triples at 8, X-Wing and XY-Wing at 9.
"""


@dataclass(frozen=True, slots=True)
class Rating:
    """A level, and the measurements it came from."""

    level: int
    givens: int
    visibility: float
    ceiling: Technique | None
    solved: bool
    """False when the catalogue could not finish the grid — level 10."""

    techniques: tuple[str, ...]
    """French names of the techniques the grid required, cheapest first."""

    @property
    def name(self) -> str:
        return BY_NUMBER[self.level].name

    @property
    def headline(self) -> str:
        """The sentence printed at the top of the sheet."""
        return f"Niveau {self.level} sur {len(LEVELS)} — {self.name}"


def visibility_of(log: SolveLog) -> float:
    """Mean share of the remaining cells that were immediately placeable.

    An already-complete grid never takes a step; it counts as fully visible.
    """
    shares = [step.available / step.remaining for step in log.steps if step.remaining]
    return statistics.fmean(shares) if shares else 1.0


def level_of(visibility: float) -> int:
    """The level visibility alone points to, before any ceiling is applied."""
    for level in LEVELS:
        if level.number >= BEYOND_LEVEL:
            break
        if visibility >= level.min_visibility:
            return level.number
    return BEYOND_LEVEL - 1


def _ceiling_floor(ceiling: Technique | None) -> int:
    if ceiling is None:
        return 1
    return CEILING_FLOOR.get(ceiling.key, BEYOND_LEVEL)


def rate(board: Board, log: SolveLog | None = None) -> Rating:
    """Rate ``board`` from 1 to 10.

    Pass ``log`` to reuse a solve already run — the generator rates every
    candidate grid it digs, and solving twice would double its cost.
    """
    if log is None:
        log = solve_logically(board)

    visibility = visibility_of(log)
    if not log.solved:
        level = BEYOND_LEVEL
    else:
        level = max(level_of(visibility), _ceiling_floor(log.ceiling))

    return Rating(
        level=level,
        givens=board.givens,
        visibility=visibility,
        ceiling=log.ceiling,
        solved=log.solved,
        techniques=log.labels,
    )


def check_catalogue_is_covered() -> None:
    """Fail loudly if a technique was added without giving it a floor.

    Cheap insurance: a missing entry would silently rate every grid needing the
    new technique as level 10.
    """
    missing = [technique.key for technique in CATALOGUE if technique.key not in CEILING_FLOOR]
    if missing:
        raise RuntimeError(f"techniques sans plancher de niveau : {', '.join(missing)}")


check_catalogue_is_covered()
