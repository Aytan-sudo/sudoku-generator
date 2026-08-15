"""Tests for the difficulty rating."""

import random
import statistics

import pytest

from sudoku.board import Board
from sudoku.generator import dig
from sudoku.human import solve_logically
from sudoku.rating import (
    BY_NUMBER,
    CEILING_FLOOR,
    LEVELS,
    Rating,
    level_of,
    rate,
    visibility_of,
)
from sudoku.solver import complete_grid
from sudoku.techniques import CATALOGUE
from tests.grids import CLASSIC_PUZZLE, CLASSIC_SOLUTION, HARDEST_PUZZLE

# --- The scale --------------------------------------------------------------


def test_the_scale_has_ten_numbered_levels() -> None:
    assert [level.number for level in LEVELS] == list(range(1, 11))
    assert len(BY_NUMBER) == 10


def test_level_names_are_distinct_and_filled_in() -> None:
    names = [level.name for level in LEVELS]
    assert len(set(names)) == 10
    assert all(name.strip() for name in names)


def test_thresholds_decrease_with_difficulty() -> None:
    thresholds = [level.min_visibility for level in LEVELS[:9]]
    assert thresholds == sorted(thresholds, reverse=True)


def test_every_technique_has_a_level_floor() -> None:
    assert all(technique.key in CEILING_FLOOR for technique in CATALOGUE)


# --- Reading a level off visibility -----------------------------------------


@pytest.mark.parametrize(
    ("visibility", "expected"),
    [(1.0, 1), (0.5, 1), (0.42, 1), (0.41, 2), (0.30, 3), (0.20, 6), (0.10, 9), (0.0, 9)],
)
def test_level_of_visibility(visibility: float, expected: int) -> None:
    assert level_of(visibility) == expected


def test_visibility_alone_never_reaches_level_ten() -> None:
    assert level_of(0.0) == 9


def test_visibility_is_a_share() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE))
    assert 0.0 < visibility_of(log) <= 1.0


def test_a_complete_grid_counts_as_fully_visible() -> None:
    log = solve_logically(Board.from_string(CLASSIC_SOLUTION))
    assert visibility_of(log) == 1.0


# --- Rating a grid ----------------------------------------------------------


def test_a_grid_beyond_the_catalogue_is_level_ten() -> None:
    rating = rate(Board.from_string(HARDEST_PUZZLE))
    assert rating.level == 10
    assert not rating.solved
    assert rating.name == "Diabolique"


def test_the_classic_puzzle_lands_in_the_easy_half() -> None:
    rating = rate(Board.from_string(CLASSIC_PUZZLE))
    assert rating.solved
    assert 1 <= rating.level <= 6
    assert rating.givens == 30
    assert rating.techniques


def test_headline_reads_as_a_sentence() -> None:
    rating = rate(Board.from_string(CLASSIC_PUZZLE))
    assert rating.headline == f"Niveau {rating.level} sur 10 — {rating.name}"


def test_rating_reuses_a_log_it_is_handed() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    log = solve_logically(board)
    assert rate(board, log) == rate(board)


def test_rating_is_deterministic() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    assert rate(board) == rate(board)


def test_rating_does_not_mutate_the_grid() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    before = board.to_string()
    rate(board)
    assert board.to_string() == before


# --- Properties across a sample ---------------------------------------------


def sample() -> list[tuple[int, Rating]]:
    rng = random.Random(4242)
    return [
        (floor, rate(dig(complete_grid(rng), rng, floor)))
        for floor in (52, 44, 38, 34, 30, 25)
        for _ in range(8)
    ]


def test_every_level_is_on_the_scale() -> None:
    for _, rating in sample():
        assert 1 <= rating.level <= 10
        assert rating.name


def test_the_technique_ceiling_is_always_respected() -> None:
    """A grid that forced a harder technique may never be rated below its floor."""
    for _, rating in sample():
        if rating.solved and rating.ceiling is not None:
            assert rating.level >= CEILING_FLOOR[rating.ceiling.key]


def test_an_unsolved_grid_is_always_level_ten() -> None:
    for _, rating in sample():
        if not rating.solved:
            assert rating.level == 10


def test_emptier_grids_rate_harder_on_average() -> None:
    """The property the whole scale rests on, checked end to end."""
    by_floor: dict[int, list[int]] = {}
    for floor, rating in sample():
        by_floor.setdefault(floor, []).append(rating.level)
    averages = [statistics.fmean(by_floor[floor]) for floor in sorted(by_floor, reverse=True)]
    assert averages == sorted(averages), f"niveaux non croissants : {averages}"
