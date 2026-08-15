"""Tests for the difficulty rating."""

import random
import statistics

import pytest

from sudoku.board import SIZE, Board
from sudoku.generator import dig, generate
from sudoku.human import SolveLog, solve_logically
from sudoku.rating import (
    BY_NUMBER,
    CEILING_FLOOR,
    FIRST_HARD_LEVEL,
    HARD_CUTS,
    LEVELS,
    Rating,
    elimination_pressure,
    hard_score,
    level_of,
    rate,
    visibility_of,
)
from sudoku.solver import complete_grid
from sudoku.techniques import BY_KEY, CATALOGUE, Action
from tests.grids import (
    CLASSIC_PUZZLE,
    CLASSIC_SOLUTION,
    HARDEST_PUZZLE,
    NEEDS_TECHNIQUE,
)

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


# --- Invariance -------------------------------------------------------------


def relabelled(board: Board, rng: random.Random) -> Board:
    """Return the same puzzle wearing a different costume.

    Renaming the digits, permuting bands and stacks, permuting rows inside a
    band and transposing all leave the logical problem untouched: every
    deduction available before is available after. So the rating must not move.
    A rating that wavered under these would be reading the accident of where the
    digits landed rather than the structure of the grid.
    """
    digits = list(range(1, SIZE + 1))
    rng.shuffle(digits)

    def shuffled_lines() -> list[int]:
        bands = [0, 1, 2]
        rng.shuffle(bands)
        order = []
        for band in bands:
            inner = [0, 1, 2]
            rng.shuffle(inner)
            order += [band * 3 + step for step in inner]
        return order

    rows, cols = shuffled_lines(), shuffled_lines()
    cells = [
        digits[board[row * SIZE + col] - 1] if board[row * SIZE + col] else 0
        for row in rows
        for col in cols
    ]
    twisted = Board(cells)
    if rng.random() < 0.5:
        twisted = Board([twisted[col * SIZE + row] for row in range(SIZE) for col in range(SIZE)])
    return twisted


def test_the_rating_survives_a_change_of_costume() -> None:
    rng = random.Random(4242)
    for floor in (50, 38, 30, 25):
        original = dig(complete_grid(rng), rng, floor)
        expected = rate(original)
        for _ in range(8):
            twin = rate(relabelled(original, rng))
            assert twin.level == expected.level
            assert twin.visibility == pytest.approx(expected.visibility)
            assert twin.givens == expected.givens


def test_a_relabelled_grid_is_still_a_proper_puzzle() -> None:
    rng = random.Random(99)
    original = dig(complete_grid(rng), rng, 32)
    twin = relabelled(original, rng)
    assert twin.is_valid()
    assert twin.givens == original.givens


# --- Placements and eliminations are not the same thing ----------------------


def advanced_logs() -> list[SolveLog]:
    return [solve_logically(Board.from_string(grid)) for grid in NEEDS_TECHNIQUE.values()]


def test_a_step_reports_one_kind_of_deduction() -> None:
    """No technique mixes the two, which is what lets a step carry a single action."""
    for log in advanced_logs():
        for step in log.steps:
            assert step.action in (Action.PLACE, Action.ELIMINATE)
            if BY_KEY[step.technique].cost >= 50:
                assert step.action is Action.ELIMINATE
            else:
                assert step.action is Action.PLACE


def test_visibility_ignores_elimination_steps() -> None:
    """Four struck candidates are not four placeable cells.

    Pooling them would make ``visibility_of`` measure something other than what
    its name says, so the elimination steps must leave it untouched.
    """
    for log in advanced_logs():
        placements = [step for step in log.steps if step.action is Action.PLACE]
        assert placements, "une grille résolue comporte forcément des placements"
        expected = statistics.fmean(
            step.available / step.remaining for step in placements if step.remaining
        )
        assert visibility_of(log) == pytest.approx(expected)


def test_visibility_stays_a_share_on_the_hardest_grids() -> None:
    for log in advanced_logs():
        assert 0.0 < visibility_of(log) <= 1.0


def test_elimination_pressure_is_zero_without_eliminations() -> None:
    assert elimination_pressure(solve_logically(Board.from_string(CLASSIC_PUZZLE))) == 0.0


def test_elimination_pressure_rises_where_candidates_are_struck() -> None:
    pressures = [elimination_pressure(log) for log in advanced_logs()]
    assert all(pressure >= 0.0 for pressure in pressures)
    assert any(pressure > 0.0 for pressure in pressures)


# --- The hard band is ranked by predicted human effort ----------------------


def test_the_cuts_are_ordered() -> None:
    assert HARD_CUTS[0] < HARD_CUTS[1]


def test_a_darker_grid_scores_higher() -> None:
    """Less visible means harder, so the predicted effort must rise."""
    assert hard_score(0.10, None, 26) > hard_score(0.16, None, 26)


def test_a_costlier_ceiling_scores_higher() -> None:
    cheap, dear = BY_KEY["pointing"], BY_KEY["xy_wing"]
    assert hard_score(0.14, dear, 28) > hard_score(0.14, cheap, 28)


def test_fewer_givens_score_higher() -> None:
    assert hard_score(0.14, None, 24) > hard_score(0.14, None, 30)


@pytest.mark.parametrize("level", [7, 8, 9])
def test_every_hard_level_is_reachable(level: int) -> None:
    assert generate(level, seed=500 + level).rating.level == level


def test_the_easy_half_is_untouched_by_the_hard_model() -> None:
    """Levels 1 to 6 keep reading visibility — no dataset speaks for them."""
    for level in range(1, 7):
        assert generate(level, seed=600 + level).rating.level == level


def test_the_hard_model_never_reaches_the_easy_levels() -> None:
    rng = random.Random(31)
    for _ in range(20):
        board = dig(complete_grid(rng), rng, rng.choice([26, 28, 30]))
        rating = rate(board)
        if rating.solved and rating.level >= FIRST_HARD_LEVEL:
            assert rating.level in (7, 8, 9)


def test_beyond_the_catalogue_still_wins_over_the_score() -> None:
    """Level 10 is a class apart and the hard model must not claim it."""
    assert rate(Board.from_string(HARDEST_PUZZLE)).level == 10
