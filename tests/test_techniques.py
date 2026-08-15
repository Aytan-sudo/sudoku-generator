"""Tests for the candidate state and the human solving techniques."""

import random

import pytest

from sudoku.board import CELL_COUNT, Board
from sudoku.solver import complete_grid
from sudoku.techniques import (
    CATALOGUE,
    Action,
    CandidateState,
    ContradictionError,
    Deduction,
    find_full_house,
    find_hidden_single_box,
    find_hidden_single_line,
    find_naked_single,
    up_to,
)
from tests.grids import CLASSIC_PUZZLE, CLASSIC_SOLUTION

# --- Grids built to isolate one technique each -------------------------------

# The solution with cell 40 rubbed out: its row, its column and its box are each
# left with a single hole.
FULL_HOUSE_GRID = CLASSIC_SOLUTION[:40] + "." + CLASSIC_SOLUTION[41:]

# Box 0 is missing 1, 2 and 3 from its top row. The 1s in columns 1 and 2 rule
# out two of the three cells, so the 1 can only be at cell 2 — yet that cell
# still has three candidates, so no naked single is involved.
HIDDEN_SINGLE_BOX_GRID = """
    .........
    456......
    789......
    1........
    .1.......
    .........
    .........
    .........
    .........
"""

# Row 0 has only three cells left. The 1s in columns 1 and 2 rule out two of
# them, leaving the 1 nowhere to go but cell 0. Box 0 is no help: cells 9 and 18
# still accept a 1, so only the row sees it.
HIDDEN_SINGLE_LINE_GRID = """
    ...456789
    .........
    .........
    .1.......
    .........
    .........
    .........
    ..1......
    .........
"""

# Row 0 rules out 1 to 6 at cell 0, and the 7 and 8 in column 0 rule out the
# rest: only the 9 survives. No digit is uniquely placed anywhere, so the hidden
# single techniques stay silent.
NAKED_SINGLE_GRID = """
    ...123456
    .........
    .........
    7........
    8........
    .........
    .........
    .........
    .........
"""


def state_of(text: str) -> CandidateState:
    return CandidateState.from_board(Board.from_string(text))


# --- CandidateState ---------------------------------------------------------


def test_state_does_not_mutate_the_source_board() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    state = CandidateState.from_board(board)
    state.place(2, 1)
    assert board[2] == 0


def test_marks_match_the_board_candidates() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    state = CandidateState.from_board(board)
    for index in range(CELL_COUNT):
        assert state.marks[index] == board.candidates(index)


def test_placing_clears_the_cell_and_its_peers() -> None:
    state = state_of(CLASSIC_PUZZLE)
    state.place(2, 1)
    assert state.board[2] == 1
    assert state.marks[2] == 0
    assert all(1 not in state.candidates(peer) for peer in (0, 1, 11, 20, 29))


def test_placing_an_impossible_digit_raises() -> None:
    state = state_of(CLASSIC_PUZZLE)
    with pytest.raises(ContradictionError):
        state.place(2, 5)


def test_eliminate_reports_whether_it_changed_anything() -> None:
    state = state_of(CLASSIC_PUZZLE)
    assert state.eliminate(2, 1) is True
    assert state.eliminate(2, 1) is False
    assert 1 not in state.candidates(2)


def test_apply_handles_both_kinds_of_deduction() -> None:
    state = state_of(CLASSIC_PUZZLE)
    assert state.apply(Deduction.eliminate(2, 1)) is True
    assert state.apply(Deduction.place(2, 2)) is True
    assert state.apply(Deduction.place(2, 2)) is False


def test_stuck_when_an_empty_cell_has_no_candidate() -> None:
    state = state_of(CLASSIC_PUZZLE)
    assert not state.is_stuck()
    state.marks[2] = 0
    assert state.is_stuck()


def test_a_solved_grid_is_reported_as_such() -> None:
    assert state_of(CLASSIC_SOLUTION).is_solved


# --- Full house -------------------------------------------------------------


def test_full_house_fills_the_last_hole() -> None:
    solution = Board.from_string(CLASSIC_SOLUTION)
    assert find_full_house(state_of(FULL_HOUSE_GRID)) == [Deduction.place(40, solution[40])]


def test_full_house_stays_silent_on_a_roomier_grid() -> None:
    assert find_full_house(state_of(CLASSIC_PUZZLE)) == []


# --- Hidden singles ---------------------------------------------------------


def test_hidden_single_in_a_box() -> None:
    assert find_hidden_single_box(state_of(HIDDEN_SINGLE_BOX_GRID)) == [Deduction.place(2, 1)]


def test_the_box_hidden_single_is_not_reachable_more_cheaply() -> None:
    state = state_of(HIDDEN_SINGLE_BOX_GRID)
    assert find_full_house(state) == []
    assert find_naked_single(state) == []


def test_hidden_single_in_a_line() -> None:
    assert find_hidden_single_line(state_of(HIDDEN_SINGLE_LINE_GRID)) == [Deduction.place(0, 1)]


def test_the_line_hidden_single_is_not_reachable_more_cheaply() -> None:
    state = state_of(HIDDEN_SINGLE_LINE_GRID)
    assert find_full_house(state) == []
    assert find_hidden_single_box(state) == []
    assert find_naked_single(state) == []


# --- Naked single -----------------------------------------------------------


def test_naked_single() -> None:
    assert find_naked_single(state_of(NAKED_SINGLE_GRID)) == [Deduction.place(0, 9)]


def test_the_naked_single_is_not_reachable_more_cheaply() -> None:
    state = state_of(NAKED_SINGLE_GRID)
    assert find_full_house(state) == []
    assert find_hidden_single_box(state) == []
    assert find_hidden_single_line(state) == []


# --- Soundness --------------------------------------------------------------


def test_no_technique_ever_contradicts_the_solution() -> None:
    """The property that matters, and the one that would fail silently.

    A placement must name the right digit; an elimination must never strike off
    the digit the solution needs. The second is the dangerous half: a wrong
    elimination does not crash, it quietly makes the grid unsolvable.

    Complete grids are punched with holes at several densities and every
    technique is run on the result. A sound deduction holds in every solution of
    a grid, and the grid we started from is one of them — so it must agree,
    whether or not the punched grid stayed unique.
    """
    rng = random.Random(2026)
    for _ in range(40):
        solution = complete_grid(rng)
        for holes in (20, 40, 55):
            cells = solution.cells.copy()
            for index in rng.sample(range(CELL_COUNT), holes):
                cells[index] = 0
            state = CandidateState.from_board(Board(cells))
            for technique in CATALOGUE:
                for deduction in technique.find(state):
                    truth = solution[deduction.index]
                    if deduction.action is Action.PLACE:
                        assert deduction.digit == truth, (
                            f"{technique.key} pose {deduction.digit} en case "
                            f"{deduction.index}, la solution y met {truth}"
                        )
                    else:
                        assert deduction.digit != truth, (
                            f"{technique.key} élimine {deduction.digit} de la case "
                            f"{deduction.index}, où la solution le place"
                        )


# --- Catalogue --------------------------------------------------------------


def test_catalogue_is_ordered_by_increasing_cost() -> None:
    costs = [technique.cost for technique in CATALOGUE]
    assert costs == sorted(costs)
    assert len(set(costs)) == len(costs)


def test_catalogue_keys_and_labels_are_unique() -> None:
    assert len({technique.key for technique in CATALOGUE}) == len(CATALOGUE)
    assert len({technique.label for technique in CATALOGUE}) == len(CATALOGUE)


def test_up_to_restricts_the_catalogue() -> None:
    assert [technique.key for technique in up_to(10)] == ["full_house"]
    assert len(up_to(30)) == 3
    assert up_to(1000) == CATALOGUE
    assert up_to(0) == ()
