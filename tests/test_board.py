"""Tests for the grid representation and the precomputed geometry."""

import pytest

from sudoku.board import (
    ALL_DIGITS,
    BOXES,
    CELL_COUNT,
    COLS,
    PEERS,
    ROWS,
    UNITS,
    UNITS_OF,
    Board,
    InvalidGridError,
    bit,
    digits_from_mask,
)
from tests.grids import CLASSIC_PUZZLE, CLASSIC_SOLUTION

# --- Geometry ---------------------------------------------------------------


def test_there_are_27_units_of_9_cells() -> None:
    assert len(UNITS) == 27
    assert all(len(unit) == 9 for unit in UNITS)


def test_each_unit_covers_distinct_cells() -> None:
    for unit in UNITS:
        assert len(set(unit)) == 9


def test_each_cell_belongs_to_exactly_three_units() -> None:
    for index in range(CELL_COUNT):
        assert len(UNITS_OF[index]) == 3


def test_each_cell_has_twenty_peers() -> None:
    for index in range(CELL_COUNT):
        assert len(PEERS[index]) == 20
        assert index not in PEERS[index]


def test_peer_relation_is_symmetric() -> None:
    for index in range(CELL_COUNT):
        for peer in PEERS[index]:
            assert index in PEERS[peer]


def test_rows_columns_and_boxes_hold_the_expected_cells() -> None:
    assert ROWS[0] == tuple(range(9))
    assert COLS[0] == tuple(range(0, CELL_COUNT, 9))
    assert BOXES[0] == (0, 1, 2, 9, 10, 11, 18, 19, 20)
    assert BOXES[8] == (60, 61, 62, 69, 70, 71, 78, 79, 80)


# --- Masks ------------------------------------------------------------------


def test_all_digits_mask_holds_nine_bits() -> None:
    assert ALL_DIGITS.bit_count() == 9
    assert digits_from_mask(ALL_DIGITS) == (1, 2, 3, 4, 5, 6, 7, 8, 9)


def test_bit_and_digits_from_mask_round_trip() -> None:
    assert digits_from_mask(bit(1) | bit(5) | bit(9)) == (1, 5, 9)
    assert digits_from_mask(0) == ()


# --- Parsing ----------------------------------------------------------------


def test_parses_and_serialises_a_grid() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    assert board.to_string() == CLASSIC_PUZZLE.replace("0", ".")


def test_accepts_dots_zeros_and_underscores_as_empty() -> None:
    dotted = CLASSIC_PUZZLE.replace("0", ".")
    underscored = CLASSIC_PUZZLE.replace("0", "_")
    assert Board.from_string(dotted).cells == Board.from_string(CLASSIC_PUZZLE).cells
    assert Board.from_string(underscored).cells == Board.from_string(CLASSIC_PUZZLE).cells


def test_ignores_whitespace_and_newlines() -> None:
    pretty = "\n".join(CLASSIC_PUZZLE[start : start + 9] for start in range(0, CELL_COUNT, 9))
    assert Board.from_string(pretty).cells == Board.from_string(CLASSIC_PUZZLE).cells


def test_str_renders_nine_lines() -> None:
    assert str(Board.from_string(CLASSIC_PUZZLE)).splitlines() == [
        "53..7....",
        "6..195...",
        ".98....6.",
        "8...6...3",
        "4..8.3..1",
        "7...2...6",
        ".6....28.",
        "...419..5",
        "....8..79",
    ]


@pytest.mark.parametrize("text", ["", "123", "1" * 82])
def test_rejects_wrong_length(text: str) -> None:
    with pytest.raises(InvalidGridError):
        Board.from_string(text)


def test_rejects_unexpected_character() -> None:
    with pytest.raises(InvalidGridError):
        Board.from_string("x" + CLASSIC_PUZZLE[1:])


def test_rejects_out_of_range_value() -> None:
    with pytest.raises(InvalidGridError):
        Board([10] + [0] * 80)


# --- Counting and state -----------------------------------------------------


def test_empty_board_is_blank_and_valid() -> None:
    board = Board.empty()
    assert board.givens == 0
    assert not board.is_complete
    assert board.is_valid()
    assert len(board.empty_cells()) == CELL_COUNT


def test_counts_givens() -> None:
    assert Board.from_string(CLASSIC_PUZZLE).givens == 30
    assert Board.from_string(CLASSIC_SOLUTION).givens == CELL_COUNT


def test_solution_is_complete_and_solved() -> None:
    board = Board.from_string(CLASSIC_SOLUTION)
    assert board.is_complete
    assert board.is_solved()


def test_copy_is_independent() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    clone = board.copy()
    clone[2] = 9
    assert board[2] == 0


# --- Rules ------------------------------------------------------------------


def test_detects_duplicate_in_a_row() -> None:
    board = Board.empty()
    board[0] = 5
    board[8] = 5
    assert not board.is_valid()


def test_detects_duplicate_in_a_column() -> None:
    board = Board.empty()
    board[0] = 5
    board[72] = 5
    assert not board.is_valid()


def test_detects_duplicate_in_a_box() -> None:
    board = Board.empty()
    board[0] = 5
    board[20] = 5
    assert not board.is_valid()


def test_complete_but_invalid_grid_is_not_solved() -> None:
    board = Board([1] * CELL_COUNT)
    assert board.is_complete
    assert not board.is_solved()


# --- Candidates -------------------------------------------------------------


def test_filled_cell_has_no_candidate() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    assert board.candidates(0) == 0
    assert board.candidate_digits(0) == ()


def test_every_digit_is_a_candidate_on_an_empty_grid() -> None:
    assert Board.empty().candidates(40) == ALL_DIGITS


def test_candidates_exclude_peers() -> None:
    board = Board.from_string(CLASSIC_PUZZLE)
    # Row 0 is "53..7....", so cell 2 sits with 5, 3 and 7 in its row, 8 and 9
    # below it in its box, and 6 further down its column.
    assert board.candidate_digits(2) == (1, 2, 4)


def test_solution_digit_is_always_among_the_candidates() -> None:
    puzzle = Board.from_string(CLASSIC_PUZZLE)
    solution = Board.from_string(CLASSIC_SOLUTION)
    for index in puzzle.empty_cells():
        assert puzzle.candidates(index) & bit(solution[index])
