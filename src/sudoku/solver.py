"""Machine solver: bitmask backtracking with a minimum-remaining-values heuristic.

This solver makes no attempt to reason like a player — that is the job of the
human solver, which rates difficulty. Here only two questions matter, and a
single search answers both: does this grid have a solution, and does it have
*exactly one*? The generator asks the second question after every cell it
removes, so the search stops as soon as the requested number of solutions has
been found.

Used digits are tracked as one mask per row, per column and per box, so the
candidates of a cell come from three lookups and a bitwise OR rather than a walk
over its twenty peers.
"""

from __future__ import annotations

import random

from sudoku.board import (
    ALL_DIGITS,
    BOX_OF,
    CELL_COUNT,
    COL_OF,
    ROW_OF,
    SIZE,
    Board,
    bit,
    digits_from_mask,
)

__all__ = ["complete_grid", "count_solutions", "has_unique_solution", "solve"]


def _unit_masks(cells: list[int]) -> tuple[list[int], list[int], list[int]]:
    """Build the used-digit masks for every row, column and box."""
    rows = [0] * SIZE
    cols = [0] * SIZE
    boxes = [0] * SIZE
    for index, digit in enumerate(cells):
        if digit:
            flag = bit(digit)
            rows[ROW_OF[index]] |= flag
            cols[COL_OF[index]] |= flag
            boxes[BOX_OF[index]] |= flag
    return rows, cols, boxes


def _search(
    cells: list[int],
    rows: list[int],
    cols: list[int],
    boxes: list[int],
    limit: int,
    first: list[list[int]],
    rng: random.Random | None,
) -> int:
    """Count solutions, stopping at ``limit``, recording the first one in ``first``."""
    # Branch on the most constrained cell: it prunes the tree fastest, and a cell
    # with a single candidate is as good as it gets, so stop looking there.
    target = -1
    target_mask = 0
    fewest = SIZE + 1
    for index in range(CELL_COUNT):
        if cells[index]:
            continue
        mask = ALL_DIGITS & ~(rows[ROW_OF[index]] | cols[COL_OF[index]] | boxes[BOX_OF[index]])
        available = mask.bit_count()
        if available == 0:
            return 0
        if available < fewest:
            target, target_mask, fewest = index, mask, available
            if available == 1:
                break

    if target < 0:
        if not first:
            first.append(cells.copy())
        return 1

    candidates = list(digits_from_mask(target_mask))
    if rng is not None:
        rng.shuffle(candidates)

    row, col, box = ROW_OF[target], COL_OF[target], BOX_OF[target]
    found = 0
    for digit in candidates:
        flag = bit(digit)
        cells[target] = digit
        rows[row] |= flag
        cols[col] |= flag
        boxes[box] |= flag

        found += _search(cells, rows, cols, boxes, limit - found, first, rng)

        cells[target] = 0
        rows[row] &= ~flag
        cols[col] &= ~flag
        boxes[box] &= ~flag

        if found >= limit:
            break
    return found


def solve(board: Board, rng: random.Random | None = None) -> Board | None:
    """Return one solution of ``board``, or None if it has none.

    Passing ``rng`` shuffles the candidate order at every branch, which turns a
    solve of the empty grid into a uniform-ish random complete grid. Determinism
    is preserved: the same seeded generator always yields the same solution.
    """
    if not board.is_valid():
        return None
    cells = board.cells.copy()
    rows, cols, boxes = _unit_masks(cells)
    first: list[list[int]] = []
    if _search(cells, rows, cols, boxes, 1, first, rng) == 0:
        return None
    return Board(first[0])


def count_solutions(board: Board, limit: int = 2) -> int:
    """Count solutions of ``board``, giving up once ``limit`` have been found.

    The default of 2 is what uniqueness testing needs: the exact count of an
    under-constrained grid is expensive and never useful here.
    """
    if limit < 1:
        raise ValueError("limit doit valoir au moins 1")
    if not board.is_valid():
        return 0
    cells = board.cells.copy()
    rows, cols, boxes = _unit_masks(cells)
    return _search(cells, rows, cols, boxes, limit, [], None)


def has_unique_solution(board: Board) -> bool:
    """True when ``board`` admits exactly one solution."""
    return count_solutions(board, limit=2) == 1


def complete_grid(rng: random.Random | None = None) -> Board:
    """Return a random complete, valid grid."""
    solution = solve(Board.empty(), rng=rng)
    if solution is None:  # pragma: no cover - the empty grid is always solvable
        raise RuntimeError("la grille vide devrait toujours admettre une solution")
    return solution
