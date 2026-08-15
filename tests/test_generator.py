"""Tests for the puzzle generator."""

import random

import pytest

from sudoku.board import CELL_COUNT, Board
from sudoku.generator import (
    GIVENS_TARGET,
    MAX_GIVENS,
    MIN_GIVENS,
    GenerationError,
    dig,
    generate,
    generate_many,
)
from sudoku.rating import LEVELS
from sudoku.solver import complete_grid, has_unique_solution, solve
from tests.grids import CLASSIC_SOLUTION

LEVEL_NUMBERS = [level.number for level in LEVELS]


# --- Digging ----------------------------------------------------------------


def test_digging_preserves_uniqueness() -> None:
    rng = random.Random(11)
    for _ in range(5):
        assert has_unique_solution(dig(complete_grid(rng), rng, 30))


def test_digging_reaches_the_target() -> None:
    rng = random.Random(12)
    for target in (60, 45, 30):
        assert dig(complete_grid(rng), rng, target).givens == target


def test_digging_leaves_the_source_untouched() -> None:
    rng = random.Random(13)
    board = Board.from_string(CLASSIC_SOLUTION)
    dig(board, rng, 30)
    assert board.to_string() == CLASSIC_SOLUTION


def test_digging_stops_when_no_cell_can_go() -> None:
    """Asking for the impossible yields the emptiest grid uniqueness allows."""
    rng = random.Random(14)
    board = dig(complete_grid(rng), rng, 0)
    assert board.givens > 0
    assert has_unique_solution(board)


def test_digging_an_already_empty_grid_is_harmless() -> None:
    rng = random.Random(15)
    assert dig(Board.empty(), rng, 30).givens == 0


# --- Targets ----------------------------------------------------------------


def test_every_level_has_a_starting_range() -> None:
    assert sorted(GIVENS_TARGET) == LEVEL_NUMBERS


def test_starting_ranges_are_ordered_and_within_bounds() -> None:
    previous_low = MAX_GIVENS + 1
    for level in LEVEL_NUMBERS:
        low, high = GIVENS_TARGET[level]
        assert MIN_GIVENS <= low < high <= MAX_GIVENS
        assert low <= previous_low, "les fourchettes doivent décroître avec la difficulté"
        previous_low = low


# --- Generating -------------------------------------------------------------


@pytest.mark.parametrize("level", LEVEL_NUMBERS)
def test_generates_a_puzzle_at_the_requested_level(level: int) -> None:
    puzzle = generate(level, seed=100 + level)
    assert puzzle.rating.level == level


@pytest.mark.parametrize("level", LEVEL_NUMBERS)
def test_the_generated_grid_is_a_proper_puzzle(level: int) -> None:
    puzzle = generate(level, seed=200 + level)
    assert has_unique_solution(puzzle.board)


@pytest.mark.parametrize("level", LEVEL_NUMBERS)
def test_the_stored_solution_is_the_real_one(level: int) -> None:
    puzzle = generate(level, seed=300 + level)
    assert puzzle.solution.is_solved()
    found = solve(puzzle.board)
    assert found is not None
    assert found.to_string() == puzzle.solution.to_string()


@pytest.mark.parametrize("level", LEVEL_NUMBERS)
def test_the_grid_agrees_with_its_solution(level: int) -> None:
    puzzle = generate(level, seed=400 + level)
    for index in range(CELL_COUNT):
        if puzzle.board[index]:
            assert puzzle.board[index] == puzzle.solution[index]


def test_the_rating_matches_the_grid() -> None:
    puzzle = generate(4, seed=42)
    assert puzzle.rating.givens == puzzle.board.givens


def test_rejects_a_level_off_the_scale() -> None:
    for level in (0, 11, -1):
        with pytest.raises(ValueError, match="niveau"):
            generate(level, seed=1)


def test_gives_up_rather_than_looping_forever() -> None:
    with pytest.raises(GenerationError, match="niveau 5"):
        generate(5, seed=1, max_attempts=0)


# --- Reproducibility --------------------------------------------------------


def test_the_same_seed_yields_the_same_puzzle() -> None:
    first, second = generate(3, seed=77), generate(3, seed=77)
    assert first.board.to_string() == second.board.to_string()
    assert first.rating == second.rating


def test_different_seeds_yield_different_puzzles() -> None:
    grids = {generate(3, seed=seed).board.to_string() for seed in range(6)}
    assert len(grids) == 6


def test_a_drawn_seed_is_recorded_and_replays() -> None:
    puzzle = generate(2)
    assert generate(2, seed=puzzle.seed).board.to_string() == puzzle.board.to_string()


# --- Identifier -------------------------------------------------------------


def test_identifier_is_short_stable_and_grid_specific() -> None:
    puzzle = generate(3, seed=55)
    assert len(puzzle.identifier) == 4
    assert int(puzzle.identifier, 16) >= 0
    assert puzzle.identifier == generate(3, seed=55).identifier
    assert puzzle.identifier != generate(3, seed=56).identifier


# --- Batches ----------------------------------------------------------------


def test_a_batch_is_all_at_the_level_and_all_distinct() -> None:
    puzzles = generate_many(4, count=5, seed=9)
    assert len(puzzles) == 5
    assert all(puzzle.rating.level == 4 for puzzle in puzzles)
    assert len({puzzle.board.to_string() for puzzle in puzzles}) == 5


def test_a_batch_replays_from_its_seed() -> None:
    first = [puzzle.board.to_string() for puzzle in generate_many(2, count=3, seed=8)]
    second = [puzzle.board.to_string() for puzzle in generate_many(2, count=3, seed=8)]
    assert first == second


def test_each_puzzle_of_a_batch_replays_on_its_own() -> None:
    for puzzle in generate_many(2, count=3, seed=8):
        assert generate(2, seed=puzzle.seed).board.to_string() == puzzle.board.to_string()


def test_a_batch_needs_at_least_one_puzzle() -> None:
    with pytest.raises(ValueError, match="count"):
        generate_many(3, count=0)
