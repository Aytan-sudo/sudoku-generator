"""Grids as text, for looking at things without opening a PDF viewer."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from sudoku.board import BOX_SIZE, SIZE, Board
from sudoku.generator import Puzzle
from sudoku.render.base import Cover, Renderer

TOP = "┌───────┬───────┬───────┐"
MIDDLE = "├───────┼───────┼───────┤"
BOTTOM = "└───────┴───────┴───────┘"


def board_to_text(board: Board) -> str:
    """Render ``board`` as a framed block of nine rows, empty cells shown as dots."""
    lines = [TOP]
    for row in range(SIZE):
        cells = [board[row * SIZE + col] for col in range(SIZE)]
        groups = [
            " ".join(str(digit) if digit else "." for digit in cells[start : start + BOX_SIZE])
            for start in range(0, SIZE, BOX_SIZE)
        ]
        lines.append("│ " + " │ ".join(groups) + " │")
        if row % BOX_SIZE == BOX_SIZE - 1 and row != SIZE - 1:
            lines.append(MIDDLE)
    lines.append(BOTTOM)
    return "\n".join(lines)


def puzzle_to_text(puzzle: Puzzle, *, solution: bool = False) -> str:
    """Render a puzzle with its heading, and optionally its solution below."""
    rating = puzzle.rating
    parts = [
        f"Sudoku · {rating.headline}",
        f"n° {puzzle.identifier} · {rating.givens} indices · "
        f"visibilité {rating.visibility:.0%} · seed {puzzle.seed}",
        board_to_text(puzzle.board),
    ]
    if solution:
        parts += ["Solution", board_to_text(puzzle.solution)]
    return "\n".join(parts)


def _heading(cover: Cover, player: str | None) -> str:
    lines = [cover.title]
    if cover.subtitle:
        lines.append(cover.subtitle)
    if player:
        lines.append(f"Carnet de : {player}")
    return "\n".join(lines)


class TextRenderer(Renderer):
    """Writes the same booklet as plain text."""

    def render(
        self,
        puzzles: Sequence[Puzzle],
        path: Path,
        *,
        solutions: bool = False,
        cover: Cover | None = None,
        player: str | None = None,
    ) -> None:
        if not puzzles:
            raise ValueError("aucune grille à rendre")
        blocks = [puzzle_to_text(puzzle, solution=solutions) for puzzle in puzzles]
        if cover:
            blocks.insert(0, _heading(cover, player))
        path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

    def render_solutions(
        self,
        puzzles: Sequence[Puzzle],
        path: Path,
        *,
        cover: Cover | None = None,
    ) -> None:
        if not puzzles:
            raise ValueError("aucune grille à rendre")
        blocks = [
            f"n° {puzzle.identifier} · niveau {puzzle.rating.level}\n"
            f"{board_to_text(puzzle.solution)}"
            for puzzle in puzzles
        ]
        if cover:
            blocks.insert(0, _heading(cover, None))
        path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
