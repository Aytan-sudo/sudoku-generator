"""Producing a grid at a requested level.

The method is the classic one: start from a complete grid and remove cells for
as long as the solution stays unique. What it cannot do is *aim*. The sample in
``tools/calibrate.py`` shows why — at 38 givens the rating ranges from 1 to 8, so
a given count picks a neighbourhood, never a level.

Hence generate, rate, retry. Between attempts the target given count is nudged in
the direction of the miss, which is what keeps the loop short: measured
acceptance runs from 18% to 70% depending on the level, so a handful of attempts
suffices, and the nudge absorbs the levels whose thresholds are still
provisional.

Checking the technique ceiling after every single removal was considered and
dropped. It would cost a full logical solve per removal, some fifty per grid, to
buy an acceptance rate the retry loop already reaches for a tenth of the price.
"""

from __future__ import annotations

import hashlib
import random
import secrets
from dataclasses import dataclass

from sudoku.board import CELL_COUNT, Board
from sudoku.human import solve_logically
from sudoku.rating import BY_NUMBER, LEVELS, Rating, rate
from sudoku.solver import complete_grid, has_unique_solution

__all__ = ["GenerationError", "Puzzle", "dig", "generate", "generate_many"]

MIN_GIVENS = 22
"""Below this, uniqueness almost never survives random digging."""

MAX_GIVENS = 60

GIVENS_TARGET: dict[int, tuple[int, int]] = {
    1: (50, 58),
    2: (44, 50),
    3: (40, 45),
    4: (36, 41),
    5: (33, 37),
    6: (31, 34),
    7: (29, 32),
    8: (27, 30),
    9: (25, 28),
    10: (22, 27),
}
"""Where to start digging for each level, from the medians measured per given
count. A starting neighbourhood, not a promise: the rating decides."""

DRIFT = 6
"""How far the nudge may wander outside a level's nominal range."""


class GenerationError(RuntimeError):
    """Raised when no grid at the requested level turned up in time."""


@dataclass(frozen=True, slots=True)
class Puzzle:
    """A grid, its solution, and how it was rated."""

    board: Board
    solution: Board
    rating: Rating
    seed: int
    """Reproduces this exact puzzle when handed back to :func:`generate`."""

    @property
    def identifier(self) -> str:
        """Short stable tag for the footer of the sheet."""
        return hashlib.blake2b(self.board.to_string().encode(), digest_size=2).hexdigest()


def dig(board: Board, rng: random.Random, target_givens: int) -> Board:
    """Remove cells in random order while the solution stays unique.

    Stops once ``target_givens`` is reached, or earlier if every remaining cell
    turns out to be load-bearing. Works on a copy.
    """
    working = board.copy()
    order = list(range(CELL_COUNT))
    rng.shuffle(order)
    givens = working.givens

    for index in order:
        if givens <= target_givens:
            break
        kept = working[index]
        if not kept:
            continue
        working[index] = 0
        if has_unique_solution(working):
            givens -= 1
        else:
            working[index] = kept

    return working


def generate(level: int, seed: int | None = None, max_attempts: int = 300) -> Puzzle:
    """Return a puzzle rated exactly ``level``.

    ``seed`` makes the result reproducible; omitted, one is drawn and recorded on
    the puzzle so the grid can be produced again later.
    """
    if level not in BY_NUMBER:
        raise ValueError(f"niveau {level} hors de 1-{len(LEVELS)}")
    if seed is None:
        seed = secrets.randbits(32)

    rng = random.Random(seed)
    low, high = GIVENS_TARGET[level]
    floor = max(MIN_GIVENS, low - DRIFT)
    ceiling = min(MAX_GIVENS, high + DRIFT)
    target = rng.randint(low, high)

    for _ in range(max_attempts):
        solution = complete_grid(rng)
        board = dig(solution, rng, target)
        rating = rate(board, solve_logically(board))
        if rating.level == level:
            return Puzzle(board=board, solution=solution, rating=rating, seed=seed)
        # Fewer givens means harder, so a grid that came out too easy calls for
        # a deeper dig next time, and one that came out too hard for a shallower.
        target += -1 if rating.level < level else 1
        target = min(max(target, floor), ceiling)

    raise GenerationError(
        f"aucune grille de niveau {level} après {max_attempts} essais (seed {seed})"
    )


def generate_many(level: int, count: int, seed: int | None = None) -> list[Puzzle]:
    """Return ``count`` distinct puzzles at ``level``.

    Each puzzle gets its own seed drawn from the master one, so a single seed
    reproduces the whole batch while every grid stays independently reproducible.
    """
    if count < 1:
        raise ValueError("count doit valoir au moins 1")
    if seed is None:
        seed = secrets.randbits(32)

    rng = random.Random(seed)
    puzzles: list[Puzzle] = []
    seen: set[str] = set()

    while len(puzzles) < count:
        puzzle = generate(level, seed=rng.randrange(2**32))
        if puzzle.board.to_string() in seen:
            continue
        seen.add(puzzle.board.to_string())
        puzzles.append(puzzle)

    return puzzles
