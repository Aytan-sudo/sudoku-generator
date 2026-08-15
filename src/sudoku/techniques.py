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
from itertools import combinations

from sudoku.board import (
    BOX_OF,
    BOXES,
    CELL_COUNT,
    COL_OF,
    COLS,
    DIGITS,
    PEERS,
    ROW_OF,
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


# --- Locked candidates ------------------------------------------------------


def _pointing(
    state: CandidateState,
    lines: Sequence[tuple[int, ...]],
    line_of: Sequence[int],
) -> list[Deduction]:
    """A digit confined to one line *within a box* leaves that line elsewhere."""
    found = []
    for box_index, box in enumerate(BOXES):
        for digit in DIGITS:
            flag = bit(digit)
            spots = [index for index in box if state.marks[index] & flag]
            if len(spots) < 2:
                continue
            touched = {line_of[index] for index in spots}
            if len(touched) != 1:
                continue
            for index in lines[touched.pop()]:
                if BOX_OF[index] != box_index and state.marks[index] & flag:
                    found.append(Deduction.eliminate(index, digit))
    return found


def _claiming(
    state: CandidateState,
    lines: Sequence[tuple[int, ...]],
    line_of: Sequence[int],
) -> list[Deduction]:
    """A digit confined to one box *within a line* leaves that box elsewhere."""
    found = []
    for line_index, line in enumerate(lines):
        for digit in DIGITS:
            flag = bit(digit)
            spots = [index for index in line if state.marks[index] & flag]
            if len(spots) < 2:
                continue
            touched = {BOX_OF[index] for index in spots}
            if len(touched) != 1:
                continue
            for index in BOXES[touched.pop()]:
                if line_of[index] != line_index and state.marks[index] & flag:
                    found.append(Deduction.eliminate(index, digit))
    return found


def find_pointing(state: CandidateState) -> list[Deduction]:
    """The 6s in this box all sit on one row, so no other 6 fits that row."""
    return _unique(_pointing(state, ROWS, ROW_OF) + _pointing(state, COLS, COL_OF))


def find_claiming(state: CandidateState) -> list[Deduction]:
    """The 6s on this row all sit in one box, so no other 6 fits that box."""
    return _unique(_claiming(state, ROWS, ROW_OF) + _claiming(state, COLS, COL_OF))


# --- Subsets ----------------------------------------------------------------


def _naked_subset(state: CandidateState, size: int) -> list[Deduction]:
    """``size`` cells sharing exactly ``size`` digits own them outright."""
    found = []
    for unit in UNITS:
        usable = [index for index in unit if 2 <= state.marks[index].bit_count() <= size]
        for combo in combinations(usable, size):
            shared = 0
            for index in combo:
                shared |= state.marks[index]
            if shared.bit_count() != size:
                continue
            for index in unit:
                if index in combo:
                    continue
                for digit in digits_from_mask(state.marks[index] & shared):
                    found.append(Deduction.eliminate(index, digit))
    return _unique(found)


def _hidden_subset(state: CandidateState, size: int) -> list[Deduction]:
    """``size`` digits confined to exactly ``size`` cells evict everything else."""
    found = []
    for unit in UNITS:
        spots = {
            digit: [index for index in unit if state.marks[index] & bit(digit)] for digit in DIGITS
        }
        usable = [digit for digit in DIGITS if 2 <= len(spots[digit]) <= size]
        for combo in combinations(usable, size):
            cells: set[int] = set()
            shared = 0
            for digit in combo:
                cells.update(spots[digit])
                shared |= bit(digit)
            if len(cells) != size:
                continue
            for index in cells:
                for digit in digits_from_mask(state.marks[index] & ~shared):
                    found.append(Deduction.eliminate(index, digit))
    return _unique(found)


def find_naked_pair(state: CandidateState) -> list[Deduction]:
    """Two cells with the same two candidates: nobody else in the unit gets them."""
    return _naked_subset(state, 2)


def find_naked_triple(state: CandidateState) -> list[Deduction]:
    """The same with three cells — harder to spot, as no cell need hold all three."""
    return _naked_subset(state, 3)


def find_hidden_pair(state: CandidateState) -> list[Deduction]:
    """Two digits that fit only two cells: those cells hold nothing else."""
    return _hidden_subset(state, 2)


def find_hidden_triple(state: CandidateState) -> list[Deduction]:
    """The same with three digits, buried among other candidates."""
    return _hidden_subset(state, 3)


# --- Fish and wings ---------------------------------------------------------


def _x_wing(
    state: CandidateState,
    lines: Sequence[tuple[int, ...]],
    line_of: Sequence[int],
    cross: Sequence[tuple[int, ...]],
    cross_of: Sequence[int],
) -> list[Deduction]:
    """Two lines where a digit fits the same two crossing lines, and only those."""
    found = []
    for digit in DIGITS:
        flag = bit(digit)
        pairs = []
        for line_index, line in enumerate(lines):
            spots = [index for index in line if state.marks[index] & flag]
            if len(spots) == 2:
                pairs.append((line_index, tuple(cross_of[index] for index in spots)))

        for (first, columns), (second, others) in combinations(pairs, 2):
            if columns != others:
                continue
            for column in columns:
                for index in cross[column]:
                    if line_of[index] not in (first, second) and state.marks[index] & flag:
                        found.append(Deduction.eliminate(index, digit))
    return found


def find_x_wing(state: CandidateState) -> list[Deduction]:
    """A rectangle of four cells that pins a digit to two lines at once."""
    return _unique(
        _x_wing(state, ROWS, ROW_OF, COLS, COL_OF) + _x_wing(state, COLS, COL_OF, ROWS, ROW_OF)
    )


def find_xy_wing(state: CandidateState) -> list[Deduction]:
    """A pivot of two candidates and two wings that corner a third digit.

    Whichever way the pivot falls, one wing is forced onto the shared digit — so
    any cell seeing both wings cannot hold it.
    """
    found = []
    bivalue = [index for index in range(CELL_COUNT) if state.marks[index].bit_count() == 2]

    for pivot in bivalue:
        pivot_mask = state.marks[pivot]
        wings = [index for index in bivalue if index in PEERS[pivot]]
        for left, right in combinations(wings, 2):
            left_mask, right_mask = state.marks[left], state.marks[right]
            shared = left_mask & right_mask & ~pivot_mask
            if shared.bit_count() != 1:
                continue
            if left_mask | right_mask != pivot_mask | shared:
                continue
            # Each wing must take a different one of the pivot's two digits.
            if (left_mask & pivot_mask) == (right_mask & pivot_mask):
                continue
            digit = digits_from_mask(shared)[0]
            for index in PEERS[left] & PEERS[right]:
                if index not in (pivot, left, right) and state.marks[index] & shared:
                    found.append(Deduction.eliminate(index, digit))
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
    Technique("pointing", "Candidats verrouillés (bloc vers ligne)", 50, find_pointing),
    Technique("claiming", "Candidats verrouillés (ligne vers bloc)", 55, find_claiming),
    Technique("naked_pair", "Paire nue", 60, find_naked_pair),
    Technique("hidden_pair", "Paire cachée", 65, find_hidden_pair),
    Technique("naked_triple", "Triplet nu", 70, find_naked_triple),
    Technique("hidden_triple", "Triplet caché", 75, find_hidden_triple),
    Technique("x_wing", "X-Wing", 80, find_x_wing),
    Technique("xy_wing", "XY-Wing", 85, find_xy_wing),
)
"""Every technique the human solver knows, cheapest first."""

BY_KEY: dict[str, Technique] = {technique.key: technique for technique in CATALOGUE}


def up_to(cost: int) -> tuple[Technique, ...]:
    """The catalogue restricted to techniques costing at most ``cost``."""
    return tuple(technique for technique in CATALOGUE if technique.cost <= cost)
