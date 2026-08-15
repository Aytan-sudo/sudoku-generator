"""Tests for the advanced techniques — the ones that produce eliminations.

Each is checked on a grid it is genuinely needed for: every cheaper technique
runs out on that grid, and nothing more expensive is called upon. Finding such
grids by hand is painful, so they were searched for with tools/find_fixtures.py
and frozen in tests/grids.py.
"""

import pytest

from sudoku.board import Board
from sudoku.human import solve_logically
from sudoku.rating import CEILING_FLOOR, rate
from sudoku.solver import has_unique_solution, solve
from sudoku.techniques import (
    BY_KEY,
    CATALOGUE,
    Action,
    CandidateState,
    up_to,
)
from tests.grids import HARDEST_PUZZLE, NEEDS_TECHNIQUE

ADVANCED = [technique.key for technique in CATALOGUE if technique.cost >= 50]


def state_of(key: str) -> CandidateState:
    return CandidateState.from_board(Board.from_string(NEEDS_TECHNIQUE[key]))


# --- The catalogue grew consistently ----------------------------------------


def test_every_advanced_technique_has_a_fixture() -> None:
    assert set(NEEDS_TECHNIQUE) == set(ADVANCED)


def test_the_catalogue_covers_the_three_upper_levels() -> None:
    assert {CEILING_FLOOR[key] for key in ADVANCED} == {7, 8, 9}


def test_costs_stay_ordered_and_distinct() -> None:
    costs = [technique.cost for technique in CATALOGUE]
    assert costs == sorted(costs)
    assert len(set(costs)) == len(costs)


# --- Each technique on the grid that needs it -------------------------------


@pytest.mark.parametrize("key", ADVANCED)
def test_the_fixture_grid_is_a_proper_puzzle(key: str) -> None:
    assert has_unique_solution(Board.from_string(NEEDS_TECHNIQUE[key]))


@pytest.mark.parametrize("key", ADVANCED)
def test_the_technique_is_the_ceiling_of_its_grid(key: str) -> None:
    log = solve_logically(Board.from_string(NEEDS_TECHNIQUE[key]))
    assert log.solved
    assert log.ceiling is not None
    assert log.ceiling.key == key


@pytest.mark.parametrize("key", ADVANCED)
def test_without_the_technique_the_grid_stalls(key: str) -> None:
    """The fixture really does hinge on it: drop it and the solver gives up."""
    cheaper = up_to(BY_KEY[key].cost - 1)
    assert not solve_logically(Board.from_string(NEEDS_TECHNIQUE[key]), cheaper).solved


@pytest.mark.parametrize("key", ADVANCED)
def test_the_solution_found_is_the_right_one(key: str) -> None:
    board = Board.from_string(NEEDS_TECHNIQUE[key])
    machine = solve(board)
    assert machine is not None
    assert solve_logically(board).board.to_string() == machine.to_string()


@pytest.mark.parametrize("key", ADVANCED)
def test_the_rating_respects_the_floor(key: str) -> None:
    rating = rate(Board.from_string(NEEDS_TECHNIQUE[key]))
    assert rating.level >= CEILING_FLOOR[key]
    assert rating.solved


# --- Eliminations -----------------------------------------------------------


@pytest.mark.parametrize("key", ADVANCED)
def test_advanced_techniques_only_eliminate(key: str) -> None:
    """They narrow candidates; placing is left to the cheap techniques."""
    board = Board.from_string(NEEDS_TECHNIQUE[key])
    state = CandidateState.from_board(board)
    for _ in range(200):
        for technique in CATALOGUE:
            found = technique.find(state)
            if not found:
                continue
            if technique.cost >= 50:
                assert all(d.action is Action.ELIMINATE for d in found)
            for deduction in found:
                state.apply(deduction)
            break
        else:
            break
        if state.is_solved:
            break


@pytest.mark.parametrize("key", ADVANCED)
def test_a_technique_never_reports_a_no_op(key: str) -> None:
    """Every deduction offered must actually change something.

    Otherwise the count of available moves — which the whole rating rests on —
    would be inflated by conclusions that lead nowhere.
    """
    state = state_of(key)
    for technique in CATALOGUE:
        for deduction in technique.find(state):
            fresh = state_of(key)
            assert fresh.apply(deduction), f"{technique.key} propose un coup sans effet"


# --- Everest still resists ---------------------------------------------------


def test_the_hardest_puzzle_remains_beyond_the_catalogue() -> None:
    """Inkala's 2012 grid needs chains, which are deliberately not implemented."""
    rating = rate(Board.from_string(HARDEST_PUZZLE))
    assert not rating.solved
    assert rating.level == 10
