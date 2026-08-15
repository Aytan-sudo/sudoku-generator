"""The printable sheet: one A4 page per grid, solutions gathered at the end.

Everything here is stated in millimetres and converted once, because the sizes
that matter are physical: an 18 mm cell is a cell a child can write a pencilled
digit into without cramping, whatever the viewer's zoom happens to be.

The one piece of real typography is the vertical placement of the digits.
Centring on the font's line height puts them visibly low, because that height
budgets for descenders no digit has. Helvetica's figures are cap-height, so the
baseline is set from the cap height instead, which lands them where the eye
expects.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from sudoku.board import CELL_COUNT, COL_OF, ROW_OF, SIZE, Board
from sudoku.generator import Puzzle
from sudoku.rating import LEVELS
from sudoku.render.base import Renderer

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

PAGE_WIDTH, PAGE_HEIGHT = A4

GRID_SIZE = 180 * mm
"""20 mm per cell. Deliberately large: a nine-year-old pencilling in a digit, and
rubbing it out again, needs the room. It leaves 15 mm side margins, comfortably
inside what any home printer can reach."""

GRID_LEFT = (PAGE_WIDTH - GRID_SIZE) / 2
GRID_TOP = 242 * mm
GRID_BOTTOM = GRID_TOP - GRID_SIZE

HEADLINE_Y = 270 * mm
GAUGE_Y = 254 * mm
NAME_Y = 46 * mm
FOOTER_Y = 18 * mm

DIGIT_RATIO = 0.55
"""Digit size as a share of the cell."""

RULE_GRAY = 0.6
"""Cell separators at 40% ink: present, but never competing with the digits."""


def _digit_baseline(centre_y: float, font_size: float, font: str = FONT) -> float:
    """Baseline that puts the optical middle of a digit at ``centre_y``.

    ReportLab exposes no cap height, but for the built-in PostScript fonts it
    coincides with the ascent, and Helvetica's figures are lining — so the ascent
    *is* the height of a digit.

    Halving the full line height instead would sink every digit by about a tenth
    of its size, since that height budgets for a descender no digit has.
    """
    ascent, _descent = pdfmetrics.getAscentDescent(font, font_size)
    return centre_y - float(ascent) / 2


def draw_grid(
    canvas: Canvas,
    board: Board,
    left: float,
    bottom: float,
    size: float,
    *,
    thin: float = 0.4,
    thick: float = 1.6,
    frame: float = 2.0,
) -> None:
    """Draw ``board`` as a square of side ``size`` with its lower-left corner given."""
    cell = size / SIZE

    canvas.setStrokeGray(RULE_GRAY)
    canvas.setLineWidth(thin)
    for step in range(1, SIZE):
        if step % 3:
            offset = step * cell
            canvas.line(left + offset, bottom, left + offset, bottom + size)
            canvas.line(left, bottom + offset, left + size, bottom + offset)

    canvas.setStrokeGray(0)
    canvas.setLineWidth(thick)
    for step in (3, 6):
        offset = step * cell
        canvas.line(left + offset, bottom, left + offset, bottom + size)
        canvas.line(left, bottom + offset, left + size, bottom + offset)

    canvas.setLineWidth(frame)
    canvas.rect(left, bottom, size, size)

    font_size = cell * DIGIT_RATIO
    canvas.setFont(FONT, font_size)
    canvas.setFillGray(0)
    for index in range(CELL_COUNT):
        digit = board[index]
        if not digit:
            continue
        centre_x = left + (COL_OF[index] + 0.5) * cell
        centre_y = bottom + size - (ROW_OF[index] + 0.5) * cell
        canvas.drawCentredString(centre_x, _digit_baseline(centre_y, font_size), str(digit))


def draw_gauge(canvas: Canvas, level: int, centre_x: float, centre_y: float) -> None:
    """Ten dots, filled up to ``level`` — the scale readable at a glance."""
    radius = 1.9 * mm
    gap = 6.5 * mm
    start = centre_x - gap * (len(LEVELS) - 1) / 2

    canvas.setLineWidth(0.6)
    for position in range(len(LEVELS)):
        canvas.setStrokeGray(0.45)
        canvas.setFillGray(0.15 if position < level else 1)
        canvas.circle(start + position * gap, centre_y, radius, stroke=1, fill=1)


def _draw_write_in_line(canvas: Canvas, baseline: float) -> None:
    """The prénom / temps line — she fills it in, and times herself."""
    canvas.setFont(FONT, 11)
    canvas.setFillGray(0.25)
    canvas.setStrokeGray(0.55)
    canvas.setLineWidth(0.5)

    middle = GRID_LEFT + GRID_SIZE * 0.58
    for label, start, end in (
        ("Prénom :", GRID_LEFT, middle - 12 * mm),
        ("Temps :", middle, GRID_LEFT + GRID_SIZE),
    ):
        canvas.drawString(start, baseline, label)
        rule_start = start + canvas.stringWidth(label, FONT, 11) + 3 * mm
        canvas.line(rule_start, baseline - 1.5 * mm, end, baseline - 1.5 * mm)


def _draw_footer(canvas: Canvas, puzzle: Puzzle, today: date) -> None:
    canvas.setFont(FONT, 8)
    canvas.setFillGray(0.5)
    canvas.drawCentredString(
        PAGE_WIDTH / 2,
        FOOTER_Y,
        f"n° {puzzle.identifier}  ·  {puzzle.board.givens} indices"
        f"  ·  seed {puzzle.seed}  ·  {today:%d/%m/%Y}",
    )


def draw_puzzle_page(canvas: Canvas, puzzle: Puzzle, today: date) -> None:
    """One grid, alone on its page, the way it will be handed over."""
    canvas.setFont(FONT_BOLD, 16)
    canvas.setFillGray(0)
    canvas.drawCentredString(PAGE_WIDTH / 2, HEADLINE_Y, f"Sudoku  ·  {puzzle.rating.headline}")

    draw_gauge(canvas, puzzle.rating.level, PAGE_WIDTH / 2, GAUGE_Y)
    draw_grid(canvas, puzzle.board, GRID_LEFT, GRID_BOTTOM, GRID_SIZE)
    _draw_write_in_line(canvas, NAME_Y)
    _draw_footer(canvas, puzzle, today)


SOLUTIONS_PER_PAGE = 6
SOLUTION_SIZE = 70 * mm
SOLUTION_COLUMNS = 2


def draw_solution_pages(canvas: Canvas, puzzles: Sequence[Puzzle]) -> None:
    """Every solution, six to a page, tagged so they can be matched back."""
    gap_x = (PAGE_WIDTH - SOLUTION_COLUMNS * SOLUTION_SIZE) / (SOLUTION_COLUMNS + 1)
    top = 258 * mm
    gap_y = 12 * mm
    caption = 7 * mm

    for start in range(0, len(puzzles), SOLUTIONS_PER_PAGE):
        canvas.showPage()
        canvas.setFont(FONT_BOLD, 14)
        canvas.setFillGray(0)
        canvas.drawCentredString(PAGE_WIDTH / 2, 272 * mm, "Solutions")

        for position, puzzle in enumerate(puzzles[start : start + SOLUTIONS_PER_PAGE]):
            column = position % SOLUTION_COLUMNS
            row = position // SOLUTION_COLUMNS
            left = gap_x + column * (SOLUTION_SIZE + gap_x)
            bottom = top - (row + 1) * SOLUTION_SIZE - row * (gap_y + caption)

            draw_grid(
                canvas,
                puzzle.solution,
                left,
                bottom,
                SOLUTION_SIZE,
                thin=0.25,
                thick=1.3,
                frame=1.5,
            )
            canvas.setFont(FONT, 8)
            canvas.setFillGray(0.45)
            canvas.drawCentredString(
                left + SOLUTION_SIZE / 2,
                bottom - 5 * mm,
                f"n° {puzzle.identifier}  ·  niveau {puzzle.rating.level}",
            )


class PdfRenderer(Renderer):
    """Writes an A4 booklet: one grid per page, solutions at the end."""

    def __init__(self, today: date | None = None) -> None:
        self.today = today or date.today()

    def render(self, puzzles: Sequence[Puzzle], path: Path, *, solutions: bool = False) -> None:
        if not puzzles:
            raise ValueError("aucune grille à rendre")

        canvas = Canvas(str(path), pagesize=A4)
        canvas.setTitle("Sudoku")
        canvas.setSubject(f"{len(puzzles)} grille(s)")

        for position, puzzle in enumerate(puzzles):
            if position:
                canvas.showPage()
            draw_puzzle_page(canvas, puzzle, self.today)

        if solutions:
            draw_solution_pages(canvas, puzzles)

        canvas.save()
