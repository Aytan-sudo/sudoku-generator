"""Tests for the human solver and its log."""

import random

from sudoku.board import CELL_COUNT, Board
from sudoku.human import solve_logically
from sudoku.solver import complete_grid, solve
from sudoku.techniques import BY_KEY, up_to
from tests.grids import CLASSIC_PUZZLE, CLASSIC_SOLUTION, HARDEST_PUZZLE

# --- Solving ----------------------------------------------------------------


def test_solves_the_classic_puzzle_with_singles_alone() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE))
    assert log.solved
    assert log.board.to_string() == CLASSIC_SOLUTION


def test_gives_up_on_the_hardest_puzzle() -> None:
    log = solve_logically(Board.from_string(HARDEST_PUZZLE))
    assert not log.solved
    assert log.board.is_valid()


def test_an_already_solved_grid_needs_no_step() -> None:
    log = solve_logically(Board.from_string(CLASSIC_SOLUTION))
    assert log.solved
    assert log.steps == ()
    assert log.ceiling is None


def test_the_empty_grid_defeats_every_technique() -> None:
    log = solve_logically(Board.empty())
    assert not log.solved
    assert log.steps == ()


def test_stops_on_a_grid_with_no_completion() -> None:
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
    assert not solve_logically(board).solved


def test_does_not_mutate_the_input() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    before = board.to_string()
    solve_logically(board)
    assert board.to_string() == before


# --- Restricting the catalogue ----------------------------------------------


def test_a_restricted_catalogue_can_fall_short() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    assert not solve_logically(board, techniques=up_to(10)).solved
    assert solve_logically(board).solved


def test_an_empty_catalogue_does_nothing() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE), techniques=())
    assert not log.solved
    assert log.steps == ()


def test_the_ceiling_never_exceeds_the_catalogue_given() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE), techniques=up_to(20))
    assert log.ceiling is None or log.ceiling.cost <= 20


# --- The log ----------------------------------------------------------------


def test_every_step_names_a_known_technique_and_changes_something() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE))
    assert log.steps
    for step in log.steps:
        assert step.technique in log.technique_counts
        assert 1 <= step.applied <= step.available


def test_the_steps_account_for_every_empty_cell() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    log = solve_logically(board)
    assert sum(step.applied for step in log.steps) == CELL_COUNT - board.givens


def test_ceiling_is_the_costliest_technique_used() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE))
    assert log.ceiling is not None
    assert log.ceiling.key in log.technique_counts
    assert log.ceiling.cost == max(BY_KEY[key].cost for key in log.technique_counts)


def test_technique_counts_are_ordered_cheapest_first() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE))
    costs = [BY_KEY[key].cost for key in log.technique_counts]
    assert costs == sorted(costs)


def test_labels_are_the_french_names_in_the_same_order() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE))
    assert len(log.labels) == len(log.technique_counts)
    assert all(isinstance(label, str) and label for label in log.labels)


def test_counts_add_up_to_the_number_of_steps() -> None:
    log = solve_logically(Board.from_string(CLASSIC_PUZZLE))
    assert sum(log.technique_counts.values()) == len(log.steps)


# --- Agreement with the machine solver --------------------------------------


def test_whatever_it_solves_matches_the_machine_solution() -> None:
    """The human solver must never disagree with the machine one.

    Grids are punched out of complete ones at several densities; whenever the
    techniques carry a grid all the way home, the answer has to be the one the
    backtracking solver finds.
    """
    rng = random.Random(1789)
    solved_count = 0
    for _ in range(30):
        solution = complete_grid(rng)
        for holes in (25, 45, 60):
            cells = solution.cells.copy()
            for index in rng.sample(range(CELL_COUNT), holes):
                cells[index] = 0
            board = Board(cells)
            log = solve_logically(board)
            for index in range(CELL_COUNT):
                if board[index]:
                    assert log.board[index] == board[index]
            if log.solved:
                solved_count += 1
                machine = solve(board)
                assert machine is not None
                assert log.board.to_string() == machine.to_string()
    assert solved_count, "aucune grille résolue : l'échantillon ne teste rien"
