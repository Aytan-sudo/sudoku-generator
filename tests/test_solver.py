"""Tests for the machine solver."""

import random

import pytest

from sudoku.board import CELL_COUNT, Board
from sudoku.solver import complete_grid, count_solutions, has_unique_solution, solve
from tests.grids import CLASSIC_PUZZLE, CLASSIC_SOLUTION, HARDEST_PUZZLE


def ambiguous_grid() -> Board:
    """A grid guaranteed to have several solutions.

    Every 1 and every 2 is removed from a complete grid. Swapping the two digits
    in any solution yields another valid one, so at least two exist — no need to
    trust a hand-picked example.
    """
    return Board.from_string("".join("." if char in "12" else char for char in CLASSIC_SOLUTION))


# --- Solving ----------------------------------------------------------------


def test_solves_the_classic_puzzle() -> None:
    solution = solve(Board.from_string(CLASSIC_PUZZLE))
    assert solution is not None
    assert solution.to_string() == CLASSIC_SOLUTION


def test_solution_keeps_the_givens_in_place() -> None:
    puzzle = Board.from_string(CLASSIC_PUZZLE)
    solution = solve(puzzle)
    assert solution is not None
    for index in range(CELL_COUNT):
        if puzzle[index]:
            assert solution[index] == puzzle[index]


def test_solves_the_hardest_puzzle() -> None:
    solution = solve(Board.from_string(HARDEST_PUZZLE))
    assert solution is not None
    assert solution.is_solved()


def test_an_already_solved_grid_solves_to_itself() -> None:
    board = Board.from_string(CLASSIC_SOLUTION)
    solution = solve(board)
    assert solution is not None
    assert solution.to_string() == CLASSIC_SOLUTION


def test_solves_the_empty_grid() -> None:
    solution = solve(Board.empty())
    assert solution is not None
    assert solution.is_solved()


def test_returns_none_on_a_contradictory_grid() -> None:
    board = Board.empty()
    board[0] = 5
    board[8] = 5
    assert solve(board) is None


def test_returns_none_when_no_completion_exists() -> None:
    # No rule is broken, yet cell 0 is stuck: its row rules out 1 to 8, and the 9
    # further down its column rules out the only digit left.
    board = Board.from_string("""
        .12345678
        .........
        .........
        9........
        .........
        .........
        .........
        .........
        .........
    """)
    assert board.is_valid()
    assert board.candidates(0) == 0
    assert solve(board) is None


# --- Counting solutions -----------------------------------------------------


def test_a_proper_puzzle_has_exactly_one_solution() -> None:
    assert count_solutions(Board.from_string(CLASSIC_PUZZLE)) == 1
    assert has_unique_solution(Board.from_string(CLASSIC_PUZZLE))


def test_the_hardest_puzzle_is_proper() -> None:
    assert has_unique_solution(Board.from_string(HARDEST_PUZZLE))


def test_an_ambiguous_grid_is_rejected() -> None:
    board = ambiguous_grid()
    assert count_solutions(board) == 2
    assert not has_unique_solution(board)


def test_counting_stops_at_the_limit() -> None:
    assert count_solutions(Board.empty(), limit=1) == 1
    assert count_solutions(Board.empty(), limit=5) == 5


def test_a_contradictory_grid_has_no_solution() -> None:
    board = Board.empty()
    board[0] = 5
    board[8] = 5
    assert count_solutions(board) == 0
    assert not has_unique_solution(board)


def test_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="limit"):
        count_solutions(Board.empty(), limit=0)


# --- Randomised solving -----------------------------------------------------


def test_complete_grid_is_solved() -> None:
    assert complete_grid(random.Random(0)).is_solved()


def test_the_same_seed_yields_the_same_grid() -> None:
    assert complete_grid(random.Random(7)).cells == complete_grid(random.Random(7)).cells


def test_different_seeds_yield_different_grids() -> None:
    grids = {complete_grid(random.Random(seed)).to_string() for seed in range(10)}
    assert len(grids) == 10


def test_solving_does_not_mutate_the_input() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    before = board.to_string()
    solve(board)
    count_solutions(board)
    assert board.to_string() == before
