"""Confront the rating with difficulty measured on real players.

Everything else in this project validates the rating against itself: it is
monotonic in the given count, invariant under the symmetries of a grid, and
respects its own technique floors. None of that shows a level-6 grid is harder
*for a person* than a level-5 one.

This does. The dataset published by Cloud Sudoku records, for each puzzle, how
long human players actually took and how often they gave up:

    https://github.com/synnwang/sudoku_dataset_difficulty

    uv run python tools/validate.py --dataset 20240415.csv

Two columns matter. ``D_TO`` is built from solving time alone, ``D_TR`` from time
and completion rate together. Higher means harder, so a metric that measures ease
correlates negatively.

What the sample can and cannot settle
-------------------------------------

Its 344 puzzles run from 24 to 32 givens, median 28. That covers the hard half of
this project's scale and **none of levels 1 to 5** — the ones the children's
booklets are made of. Anything measured here says nothing about them. Calibrating
the whole scale on this dataset would be trading a validated easy end for an
unvalidated one.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sudoku.board import Board
from sudoku.human import solve_logically
from sudoku.rating import rate
from sudoku.techniques import CATALOGUE, CandidateState

PLACING = tuple(technique for technique in CATALOGUE if technique.cost < 50)
ELIMINATING = tuple(technique for technique in CATALOGUE if technique.cost >= 50)

BEYOND_COST = 100
"""Stand-in ceiling cost for a grid the catalogue cannot finish."""


# --- Statistics without a dependency ----------------------------------------


def ranks(values: Sequence[float]) -> list[float]:
    """Average ranks, ties shared."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    result = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start
        while stop + 1 < len(order) and values[order[stop + 1]] == values[order[start]]:
            stop += 1
        shared = (start + stop) / 2 + 1
        for position in range(start, stop + 1):
            result[order[position]] = shared
        start = stop + 1
    return result


def pearson(left: Sequence[float], right: Sequence[float]) -> float:
    mean_left, mean_right = statistics.fmean(left), statistics.fmean(right)
    covariance = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right, strict=True))
    spread_left = sum((a - mean_left) ** 2 for a in left) ** 0.5
    spread_right = sum((b - mean_right) ** 2 for b in right) ** 0.5
    return covariance / (spread_left * spread_right) if spread_left and spread_right else 0.0


def spearman(left: Sequence[float], right: Sequence[float]) -> float:
    return pearson(ranks(left), ranks(right))


def ridge(
    design: Sequence[Sequence[float]], target: Sequence[float], penalty: float
) -> list[float]:
    """Least squares with a small ridge term, by Gauss-Jordan on the normal equations.

    A handful of features on a few hundred rows; pulling in a linear algebra
    dependency for this would cost more than it saves.
    """
    width = len(design[0])
    matrix = [
        [
            sum(row[i] * row[j] for row in design) + (penalty if i == j else 0.0)
            for j in range(width)
        ]
        for i in range(width)
    ]
    vector = [
        sum(row[i] * value for row, value in zip(design, target, strict=True)) for i in range(width)
    ]

    for column in range(width):
        pivot = max(range(column, width), key=lambda row: abs(matrix[row][column]))
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        vector[column], vector[pivot] = vector[pivot], vector[column]
        if not matrix[column][column]:
            continue
        for row in range(width):
            if row != column:
                factor = matrix[row][column] / matrix[column][column]
                for k in range(width):
                    matrix[row][k] -= factor * matrix[column][k]
                vector[row] -= factor * vector[column]

    return [vector[i] / matrix[i][i] if matrix[i][i] else 0.0 for i in range(width)]


# --- Features ---------------------------------------------------------------


def move_counts(board: Board) -> list[int]:
    """Moves on offer at each turn, playing one at a time.

    Pelánek's model of a solver: take the cheapest technique that works, count
    what it offers, play a single one of them, start over. The elimination
    techniques only unblock — they place nothing, so they are not turns.
    """
    state = CandidateState.from_board(board)
    offered: list[int] = []

    for _ in range(200):
        if state.is_solved or state.is_stuck():
            break

        placements = next(
            (found for technique in PLACING if (found := technique.find(state))), None
        )
        if placements:
            offered.append(len(placements))
            state.apply(placements[0])
            continue

        struck = next(
            (found for technique in ELIMINATING if (found := technique.find(state))), None
        )
        if not struck:
            break
        for deduction in struck:
            state.apply(deduction)

    return offered


@dataclass(frozen=True, slots=True)
class Features:
    """What is measured about one puzzle."""

    visibility: float
    dependency: float
    """Mean moves on offer over the first 25 turns."""

    forced: float
    """Share of turns offering exactly one move."""

    longest_forced: int
    ceiling: float
    moves: int
    givens: int

    def row(self) -> list[float]:
        return [
            1.0,
            self.visibility,
            self.dependency,
            self.forced,
            self.longest_forced / 10,
            self.ceiling / BEYOND_COST,
            self.moves / 50,
            self.givens / 30,
        ]


NAMES = ("const", "visibilité", "dépendance", "forcés", "chaîne", "plafond", "coups", "indices")


def measure(board: Board) -> Features | None:
    log = solve_logically(board)
    rating = rate(board, log)
    offered = move_counts(board)
    if not offered:
        return None

    longest = current = 0
    for count in offered:
        current = current + 1 if count == 1 else 0
        longest = max(longest, current)

    ceiling = BEYOND_COST if not rating.solved else (log.ceiling.cost if log.ceiling else 0)
    return Features(
        visibility=rating.visibility,
        dependency=statistics.fmean(offered[:25]),
        forced=sum(1 for count in offered if count == 1) / len(offered),
        longest_forced=longest,
        ceiling=ceiling,
        moves=len(offered),
        givens=board.givens,
    )


# --- Running the thing ------------------------------------------------------


def cross_validated(
    design: Sequence[Sequence[float]],
    target: Sequence[float],
    folds: int,
    seed: int,
    penalty: float,
) -> list[float]:
    """Predictions made only by models that never saw the row they predict."""
    order = list(range(len(design)))
    random.Random(seed).shuffle(order)
    predictions = [0.0] * len(design)

    for fold in range(folds):
        held = [index for position, index in enumerate(order) if position % folds == fold]
        kept = [index for position, index in enumerate(order) if position % folds != fold]
        weights = ridge([design[i] for i in kept], [target[i] for i in kept], penalty)
        for index in held:
            predictions[index] = sum(w * x for w, x in zip(weights, design[index], strict=True))

    return predictions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="CSV de Cloud Sudoku")
    parser.add_argument("--column", default="D_TO", choices=("D_TO", "D_TR"))
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--penalty", type=float, default=1e-3)
    args = parser.parse_args()

    with args.dataset.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    design, target, features = [], [], []
    givens = []
    for row in rows:
        board = Board.from_string(row["Sudoku Puzzle"])
        measured = measure(board)
        if measured is None:
            continue
        features.append(measured)
        design.append(measured.row())
        target.append(math.log(float(row[args.column])))
        givens.append(board.givens)

    print(
        f"{len(design)} grilles · indices {min(givens)}-{max(givens)}"
        f" (médiane {sorted(givens)[len(givens) // 2]}) · cible log({args.column})\n"
    )

    print("Chaque mesure seule, en Spearman :")
    for position, name in enumerate(NAMES):
        if position == 0:
            continue
        column = [row[position] for row in design]
        print(f"  {name:<12} {spearman(column, target):+.3f}")

    predictions = cross_validated(design, target, args.folds, args.seed, args.penalty)
    print(
        f"\nModèle combiné, {args.folds} blocs, hors échantillon :"
        f"  Spearman {spearman(predictions, target):+.3f}"
        f"  Pearson {pearson(predictions, target):+.3f}"
    )

    print("\nPoids ajustés sur l'ensemble :")
    for name, weight in zip(NAMES, ridge(design, target, args.penalty), strict=True):
        print(f"  {name:<12} {weight:+.3f}")

    print(
        "\nRéserve : cet échantillon ne descend pas sous 24 indices ni au-dessus de 32."
        "\nIl ne dit rien des niveaux 1 à 5, ceux des carnets pour enfants.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
