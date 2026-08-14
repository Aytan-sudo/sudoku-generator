"""Human solving techniques, ordered from cheapest to most demanding.

Difficulty comes from *which techniques a grid forces a player to use*, so this
module is where the rating ultimately originates. Each technique inspects a
:class:`CandidateState` — a grid plus its pencil marks — and reports every
conclusion it can reach, without applying any of them. The caller decides what to
do with them, which is what lets the solver measure how many moves were on offer
at each step.

Two kinds of conclusion exist. A *placement* writes a digit into a cell; an
*elimination* only strikes a candidate off. The techniques added here all produce
placements, but the elimination path is wired up from the start so the advanced
techniques of step 7 slot in without touching the solver.

Costs are spaced by ten so later techniques can be inserted between existing ones
without renumbering.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

from sudoku.board import (
    BOXES,
    CELL_COUNT,
    COLS,
    DIGITS,
    PEERS,
    ROWS,
    UNITS,
    Board,
    bit,
    digits_from_mask,
)


class Action(Enum):
    """What a deduction asks for."""

    PLACE = "place"
    ELIMINATE = "eliminate"


@dataclass(frozen=True, slots=True)
class Deduction:
    """A single conclusion about one digit in one cell."""

    action: Action
    index: int
    digit: int

    @classmethod
    def place(cls, index: int, digit: int) -> Deduction:
        return cls(Action.PLACE, index, digit)

    @classmethod
    def eliminate(cls, index: int, digit: int) -> Deduction:
        return cls(Action.ELIMINATE, index, digit)


class ContradictionError(RuntimeError):
    """Raised when a deduction contradicts the grid it is applied to."""


@dataclass(slots=True)
class CandidateState:
    """A grid together with its pencil marks, kept in sync.

    ``marks[i]`` is the mask of digits still possible at cell ``i``, and is 0 for
    a filled cell. Maintaining it incrementally is what makes the elimination
    techniques possible at all: once a candidate has been struck off by one
    technique, every later technique sees the narrowed set.
    """

    board: Board
    marks: list[int]

    @classmethod
    def from_board(cls, board: Board) -> CandidateState:
        """Build the state of ``board``, leaving the original untouched."""
        working = board.copy()
        return cls(working, [working.candidates(index) for index in range(CELL_COUNT)])

    def candidates(self, index: int) -> tuple[int, ...]:
        """Digits still possible at ``index``."""
        return digits_from_mask(self.marks[index])

    @property
    def is_solved(self) -> bool:
        return self.board.is_solved()

    def is_stuck(self) -> bool:
        """True when an empty cell has no candidate left, so no solution exists."""
        return any(not self.board[index] and not self.marks[index] for index in range(CELL_COUNT))

    def place(self, index: int, digit: int) -> None:
        """Write ``digit`` at ``index`` and strike it off every peer."""
        if not self.marks[index] & bit(digit):
            raise ContradictionError(f"le chiffre {digit} est impossible en case {index}")
        self.board[index] = digit
        self.marks[index] = 0
        flag = ~bit(digit)
        for peer in PEERS[index]:
            self.marks[peer] &= flag

    def eliminate(self, index: int, digit: int) -> bool:
        """Strike ``digit`` off ``index``. Returns True when something changed."""
        flag = bit(digit)
        if not self.marks[index] & flag:
            return False
        self.marks[index] &= ~flag
        return True

    def apply(self, deduction: Deduction) -> bool:
        """Apply one deduction. Returns True when it changed the state."""
        if deduction.action is Action.PLACE:
            if self.board[deduction.index] == deduction.digit:
                return False
            self.place(deduction.index, deduction.digit)
            return True
        return self.eliminate(deduction.index, deduction.digit)


def _unique(deductions: Iterable[Deduction]) -> list[Deduction]:
    """Drop repeats, keeping the order in which they were found.

    A cell sits in three units, so the same conclusion is regularly reached more
    than once within a single pass.
    """
    return list(dict.fromkeys(deductions))


# --- Techniques -------------------------------------------------------------


def find_full_house(state: CandidateState) -> list[Deduction]:
    """A unit with a single empty cell: the missing digit goes there.

    The one move that needs no reasoning at all — you read off what is absent.
    """
    found = []
    for unit in UNITS:
        empty = [index for index in unit if not state.board[index]]
        if len(empty) == 1:
            digits = state.candidates(empty[0])
            if len(digits) == 1:
                found.append(Deduction.place(empty[0], digits[0]))
    return _unique(found)


def _hidden_singles(state: CandidateState, units: Sequence[tuple[int, ...]]) -> list[Deduction]:
    """A digit with a single possible cell left in a unit."""
    found = []
    for unit in units:
        for digit in DIGITS:
            flag = bit(digit)
            spots = [index for index in unit if state.marks[index] & flag]
            if len(spots) == 1:
                found.append(Deduction.place(spots[0], digit))
    return _unique(found)


def find_hidden_single_box(state: CandidateState) -> list[Deduction]:
    """Scanning a box: "where can the 7 go in here?"

    The natural beginner move — the lines crossing the box are read off visually,
    with no need to write anything down.
    """
    return _hidden_singles(state, BOXES)


def find_hidden_single_line(state: CandidateState) -> list[Deduction]:
    """The same reasoning along a row or a column.

    Much less visual than the box version: nine cells strung out in a line, so it
    takes a deliberate sweep rather than a glance.
    """
    return _hidden_singles(state, ROWS + COLS)


def find_naked_single(state: CandidateState) -> list[Deduction]:
    """A cell with a single candidate left.

    Cheap for a program, but demanding for a beginner: it means crossing the
    three units of the cell and holding the surviving digits in mind.
    """
    found = [
        Deduction.place(index, state.candidates(index)[0])
        for index in range(CELL_COUNT)
        if not state.board[index] and state.marks[index].bit_count() == 1
    ]
    return _unique(found)


# --- Catalogue --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Technique:
    """One entry of the catalogue."""

    key: str
    label: str
    """Wording used in the generated PDF, hence in French."""

    cost: int
    """Ordering weight. The solver always retries from the cheapest."""

    find: Callable[[CandidateState], list[Deduction]]


CATALOGUE: tuple[Technique, ...] = (
    Technique("full_house", "Dernière case", 10, find_full_house),
    Technique("hidden_single_box", "Chiffre unique dans un bloc", 20, find_hidden_single_box),
    Technique(
        "hidden_single_line",
        "Chiffre unique dans une ligne ou une colonne",
        30,
        find_hidden_single_line,
    ),
    Technique("naked_single", "Case à candidat unique", 40, find_naked_single),
)
"""Every technique the human solver knows, cheapest first."""

BY_KEY: dict[str, Technique] = {technique.key: technique for technique in CATALOGUE}


def up_to(cost: int) -> tuple[Technique, ...]:
    """The catalogue restricted to techniques costing at most ``cost``."""
    return tuple(technique for technique in CATALOGUE if technique.cost <= cost)
