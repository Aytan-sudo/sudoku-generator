"""Tests for the renderers."""

from datetime import date
from pathlib import Path

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from sudoku.board import Board
from sudoku.generator import Puzzle, generate
from sudoku.render.pdf import (
    DIGIT_RATIO,
    GRID_BOTTOM,
    GRID_LEFT,
    GRID_SIZE,
    GRID_TOP,
    PdfRenderer,
    _digit_baseline,
)
from sudoku.render.text import TextRenderer, board_to_text, puzzle_to_text
from tests.grids import CLASSIC_PUZZLE

FIXED_DAY = date(2026, 8, 15)


@pytest.fixture(scope="module")
def puzzles() -> list[Puzzle]:
    return [generate(level, seed=900 + level) for level in (2, 4)]


# --- Page geometry ----------------------------------------------------------


def test_the_grid_fits_the_page_with_room_to_spare() -> None:
    width, height = A4
    assert GRID_LEFT > 0
    assert width >= GRID_LEFT + GRID_SIZE
    assert GRID_BOTTOM > 0
    assert height >= GRID_TOP
    assert 10 * mm <= GRID_LEFT, "marge trop faible pour une imprimante domestique"


def test_the_grid_is_horizontally_centred() -> None:
    width, _ = A4
    assert pytest.approx(width - GRID_LEFT - GRID_SIZE) == GRID_LEFT


def test_cells_are_a_round_twenty_millimetres() -> None:
    assert pytest.approx(20 * mm) == GRID_SIZE / 9


# --- Optical centring -------------------------------------------------------


def test_a_digit_sits_centred_on_the_cell() -> None:
    """The middle of the glyph, not the middle of the line box, meets the centre."""
    centre, size = 100.0, 28.0
    ascent, _ = pdfmetrics.getAscentDescent("Helvetica", size)
    baseline = _digit_baseline(centre, size)
    assert baseline + ascent / 2 == pytest.approx(centre)


def test_centring_sits_higher_than_naive_line_centring() -> None:
    """The whole point: halving the line height would sink the digit."""
    centre, size = 100.0, 28.0
    ascent, descent = pdfmetrics.getAscentDescent("Helvetica", size)
    naive = centre - (ascent + descent) / 2
    assert _digit_baseline(centre, size) < naive


def test_digits_stay_inside_their_cell() -> None:
    cell = GRID_SIZE / 9
    assert cell * DIGIT_RATIO < cell


# --- PDF --------------------------------------------------------------------


def test_writes_a_readable_pdf(tmp_path: Path, puzzles: list[Puzzle]) -> None:
    path = tmp_path / "grilles.pdf"
    PdfRenderer(today=FIXED_DAY).render(puzzles, path)
    assert path.read_bytes().startswith(b"%PDF")


def test_one_page_per_puzzle(tmp_path: Path, puzzles: list[Puzzle]) -> None:
    path = tmp_path / "grilles.pdf"
    PdfRenderer(today=FIXED_DAY).render(puzzles, path)
    assert len(PdfReader(path).pages) == len(puzzles)


def test_solutions_add_pages(tmp_path: Path, puzzles: list[Puzzle]) -> None:
    plain, annotated = tmp_path / "a.pdf", tmp_path / "b.pdf"
    PdfRenderer(today=FIXED_DAY).render(puzzles, plain)
    PdfRenderer(today=FIXED_DAY).render(puzzles, annotated, solutions=True)
    assert len(PdfReader(annotated).pages) == len(PdfReader(plain).pages) + 1


def test_solutions_are_gathered_six_to_a_page(tmp_path: Path) -> None:
    many = [generate(1, seed=1000 + index) for index in range(7)]
    path = tmp_path / "carnet.pdf"
    PdfRenderer(today=FIXED_DAY).render(many, path, solutions=True)
    assert len(PdfReader(path).pages) == 7 + 2


def test_pages_are_a4(tmp_path: Path, puzzles: list[Puzzle]) -> None:
    path = tmp_path / "grilles.pdf"
    PdfRenderer(today=FIXED_DAY).render(puzzles, path, solutions=True)
    width, height = A4
    for page in PdfReader(path).pages:
        assert float(page.mediabox.width) == pytest.approx(width, abs=1)
        assert float(page.mediabox.height) == pytest.approx(height, abs=1)


def test_the_sheet_carries_the_level_and_the_footer(tmp_path: Path) -> None:
    puzzle = generate(3, seed=321)
    path = tmp_path / "grille.pdf"
    PdfRenderer(today=FIXED_DAY).render([puzzle], path)
    text = PdfReader(path).pages[0].extract_text()
    assert puzzle.rating.headline in text
    assert puzzle.identifier in text
    assert str(puzzle.seed) in text
    assert "15/08/2026" in text
    assert "Prénom" in text


def test_rendering_nothing_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="aucune grille"):
        PdfRenderer().render([], tmp_path / "vide.pdf")


# --- Text -------------------------------------------------------------------


def test_text_grid_has_nine_rows_inside_a_frame() -> None:
    lines = board_to_text(Board.from_string(CLASSIC_PUZZLE)).splitlines()
    assert len(lines) == 13
    assert lines[0].startswith("┌") and lines[-1].startswith("└")
    assert sum(1 for line in lines if line.startswith("│")) == 9


def test_text_grid_shows_digits_and_dots() -> None:
    text = board_to_text(Board.from_string(CLASSIC_PUZZLE))
    assert "5 3 ." in text
    assert text.count(".") == 51


def test_text_grid_of_an_empty_board_is_all_dots() -> None:
    assert board_to_text(Board.empty()).count(".") == 81


def test_puzzle_text_carries_the_heading(puzzles: list[Puzzle]) -> None:
    text = puzzle_to_text(puzzles[0])
    assert puzzles[0].rating.headline in text
    assert puzzles[0].identifier in text


def test_puzzle_text_can_include_the_solution(puzzles: list[Puzzle]) -> None:
    assert "Solution" not in puzzle_to_text(puzzles[0])
    assert "Solution" in puzzle_to_text(puzzles[0], solution=True)


def test_text_renderer_writes_every_puzzle(tmp_path: Path, puzzles: list[Puzzle]) -> None:
    path = tmp_path / "grilles.txt"
    TextRenderer().render(puzzles, path)
    text = path.read_text(encoding="utf-8")
    assert all(puzzle.identifier in text for puzzle in puzzles)


def test_text_renderer_refuses_an_empty_batch(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="aucune grille"):
        TextRenderer().render([], tmp_path / "vide.txt")
