"""Solving a grid the way a player does, and recording how it went.

The machine solver in :mod:`sudoku.solver` answers whether a grid *can* be
solved. This one answers how *hard* it is: it only ever applies techniques from
the catalogue, always retrying from the cheapest, and writes down what it used at
each step. The resulting log is the raw material the rating is computed from.

The number of moves on offer at each step is recorded alongside the technique,
because it matters as much as the technique itself. A grid that hands you eight
placements at every turn is a stroll; a grid where the very same technique yields
exactly one placement, somewhere among eighty-one cells, is a hunt.
"""

from __future__ import annotations

from dataclasses import dataclass

from sudoku.board import CELL_COUNT, Board
from sudoku.techniques import (
    BY_KEY,
    CATALOGUE,
    Action,
    CandidateState,
    ContradictionError,
    Technique,
)

__all__ = ["SolveLog", "SolveStep", "solve_logically"]


@dataclass(frozen=True, slots=True)
class SolveStep:
    """One turn of the solving loop."""

    technique: str
    """Key of the technique that produced the deductions."""

    available: int
    """How many deductions that technique offered — the choice on hand."""

    applied: int
    """How many of them actually changed the grid."""

    remaining: int
    """Empty cells when the step began.

    ``available`` alone is misleading: a nearly finished grid offers few moves
    simply because few cells are left. Dividing by this gives the share of the
    remaining work that was in plain sight, which compares across grids of very
    different fill levels.
    """

    action: Action
    """Whether this step placed digits or only struck candidates off.

    The two cannot be pooled. ``available`` counts deductions, and four
    eliminations are not four placeable cells — dividing them by the number of
    empty cells would answer no question at all. Anything reasoning about how
    much of the grid was in plain sight must keep to the placement steps.
    """


@dataclass(frozen=True, slots=True)
class SolveLog:
    """What happened while solving, and how far it got."""

    solved: bool
    steps: tuple[SolveStep, ...]
    board: Board
    """Final grid: the solution when solved, otherwise where it stalled."""

    @property
    def ceiling(self) -> Technique | None:
        """The most demanding technique the grid forced. None if it never started."""
        used = [BY_KEY[step.technique] for step in self.steps]
        return max(used, key=lambda technique: technique.cost) if used else None

    @property
    def technique_counts(self) -> dict[str, int]:
        """How many times each technique was called upon, cheapest first."""
        counts: dict[str, int] = {}
        for step in self.steps:
            counts[step.technique] = counts.get(step.technique, 0) + 1
        return {key: counts[key] for key in BY_KEY if key in counts}

    @property
    def labels(self) -> tuple[str, ...]:
        """French names of the techniques used, cheapest first."""
        return tuple(BY_KEY[key].label for key in self.technique_counts)


def solve_logically(
    board: Board,
    techniques: tuple[Technique, ...] = CATALOGUE,
) -> SolveLog:
    """Solve ``board`` using only ``techniques``, recording each step.

    Restricting ``techniques`` is how the generator checks that a grid stays
    within a difficulty band: hand it the catalogue up to a given cost, and an
    unsolved log means the grid needs more than that.

    A log with ``solved=False`` is a normal outcome, not an error — it simply
    means the catalogue ran out before the grid did.
    """
    state = CandidateState.from_board(board)
    steps: list[SolveStep] = []

    while not state.is_solved:
        if state.is_stuck():
            break

        for technique in techniques:
            found = technique.find(state)
            if not found:
                continue
            remaining = CELL_COUNT - state.board.givens
            action = found[0].action
            try:
                applied = sum(state.apply(deduction) for deduction in found)
            except ContradictionError:
                return SolveLog(solved=False, steps=tuple(steps), board=state.board)
            steps.append(SolveStep(technique.key, len(found), applied, remaining, action))
            # A technique that reports moves but changes nothing would spin the
            # loop forever; treat it as the end of the road.
            if applied == 0:
                return SolveLog(solved=False, steps=tuple(steps), board=state.board)
            break
        else:
            break

    return SolveLog(solved=state.is_solved, steps=tuple(steps), board=state.board)
