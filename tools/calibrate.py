"""Measure what actually varies with difficulty, so the rating rests on data.

The first thresholds sketched for this project came from intuition and two of
the three metrics did not survive contact with a sample: the bottleneck (the
fewest moves offered at any point of a solve) turned out to be 1 almost every
time, and the technique ceiling saturated at "hidden single in a box" across the
whole 28-55 givens range.

This script digs a large sample of grids across a range of given counts, runs the
human solver on each, and writes one row of raw measurements per grid. Analysis
happens afterwards on the CSV, so the sample is generated once and re-read as
often as needed.

    uv run python tools/calibrate.py --per-floor 50 --out sample.csv

Caveat worth keeping in mind: digging here is constrained only by uniqueness,
which gives the natural spread of what random removal produces. The generator of
step 4 will additionally refuse removals that break a technique ceiling, so its
output will be a shaped subset of this distribution, not a copy of it.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from sudoku.board import CELL_COUNT, Board
from sudoku.human import SolveLog, solve_logically
from sudoku.solver import complete_grid, has_unique_solution
from sudoku.techniques import BY_KEY, CATALOGUE

BEYOND = "beyond_catalogue"
"""Ceiling recorded when the catalogue runs out before the grid does."""

FLOORS: tuple[int, ...] = (58, 54, 50, 47, 44, 41, 38, 36, 34, *range(32, 21, -1))
"""Target given counts to dig down to, from roomy to near-minimal.

Tighter around 22-32, where the sample shows the technique ceiling starting to
bite and grids beginning to fall outside the catalogue.
"""


@dataclass(frozen=True, slots=True)
class Measurement:
    """Everything measured about one grid."""

    floor: int
    givens: int
    solved: bool
    ceiling: str
    steps: int
    placements: int
    avail_min: int
    avail_mean: float
    avail_median: float
    avail_max: int
    visibility: float
    """Mean share of the remaining cells that were immediately placeable.

    The scale-free counterpart of ``avail_mean``, which is confounded: a nearly
    full grid offers few moves only because few cells are left.
    """

    steps_single: float
    """Share of steps that offered exactly one move."""

    mean_cost: float
    """Average catalogue cost per placement — how demanding the grid was overall,
    as opposed to the ceiling, which only reports its single worst moment."""

    share_full_house: float
    share_hidden_single_box: float
    share_hidden_single_line: float
    share_naked_single: float


def dig(rng: random.Random, floor: int) -> Board:
    """Remove cells in random order while uniqueness holds, down to ``floor``."""
    board = complete_grid(rng)
    order = list(range(CELL_COUNT))
    rng.shuffle(order)
    givens = CELL_COUNT
    for index in order:
        if givens <= floor:
            break
        kept = board[index]
        board[index] = 0
        if has_unique_solution(board):
            givens -= 1
        else:
            board[index] = kept
    return board


def measure(board: Board, log: SolveLog, floor: int) -> Measurement:
    """Turn a solve log into one row of measurements."""
    available = [step.available for step in log.steps] or [0]
    visible = [step.available / step.remaining for step in log.steps if step.remaining]
    placements = sum(step.applied for step in log.steps)

    by_technique: Counter[str] = Counter()
    for step in log.steps:
        by_technique[step.technique] += step.applied

    if placements:
        mean_cost = (
            sum(BY_KEY[key].cost * count for key, count in by_technique.items()) / placements
        )
        shares = {key: by_technique[key] / placements for key in BY_KEY}
    else:
        mean_cost = 0.0
        shares = dict.fromkeys(BY_KEY, 0.0)

    ceiling = BEYOND if not log.solved else (log.ceiling.key if log.ceiling else "none")

    return Measurement(
        floor=floor,
        givens=board.givens,
        solved=log.solved,
        ceiling=ceiling,
        steps=len(log.steps),
        placements=placements,
        avail_min=min(available),
        avail_mean=round(statistics.fmean(available), 3),
        avail_median=round(statistics.median(available), 3),
        avail_max=max(available),
        visibility=round(statistics.fmean(visible) if visible else 0.0, 4),
        steps_single=round(sum(1 for count in available if count == 1) / len(available), 3),
        mean_cost=round(mean_cost, 3),
        share_full_house=round(shares["full_house"], 3),
        share_hidden_single_box=round(shares["hidden_single_box"], 3),
        share_hidden_single_line=round(shares["hidden_single_line"], 3),
        share_naked_single=round(shares["naked_single"], 3),
    )


def collect(per_floor: int, seed: int) -> list[Measurement]:
    """Dig and measure ``per_floor`` grids at each target given count."""
    rng = random.Random(seed)
    rows: list[Measurement] = []
    started = time.perf_counter()

    for position, floor in enumerate(FLOORS, start=1):
        floor_started = time.perf_counter()
        for _ in range(per_floor):
            board = dig(rng, floor)
            rows.append(measure(board, solve_logically(board), floor))
        print(
            f"  [{position:>2}/{len(FLOORS)}] plancher {floor:>2} indices — "
            f"{per_floor} grilles en {time.perf_counter() - floor_started:5.1f} s",
            file=sys.stderr,
            flush=True,
        )

    print(
        f"  {len(rows)} grilles en {time.perf_counter() - started:.1f} s",
        file=sys.stderr,
        flush=True,
    )
    return rows


def summarise(rows: list[Measurement]) -> None:
    """Print the tables worth reading before touching any threshold."""
    solved = [row for row in rows if row.solved]

    print(f"\n{len(rows)} grilles, dont {len(solved)} résolues par le catalogue\n")

    print("Plafond de technique atteint")
    print(f"  {'plafond':<24} {'n':>4} {'indices':>12} {'moy. coups':>11}")
    for ceiling, count in Counter(row.ceiling for row in rows).most_common():
        group = [row for row in rows if row.ceiling == ceiling]
        givens = [row.givens for row in group]
        means = [row.avail_mean for row in group if row.solved]
        span = f"{min(givens)}-{max(givens)}"
        mean = f"{statistics.fmean(means):.2f}" if means else "—"
        print(f"  {ceiling:<24} {count:>4} {span:>12} {mean:>11}")

    print("\nPar tranche d'indices (grilles résolues)")
    header = f"  {'indices':>8} {'n':>4} {'moy.coups':>10} {'visibilité':>11}"
    header += f" {'%1coup':>7} {'coût moy':>9} {'%hors cat.':>11}"
    print(header)
    for floor in FLOORS:
        group = [row for row in solved if row.floor == floor]
        whole = [row for row in rows if row.floor == floor]
        if not whole:
            continue
        beyond = sum(1 for row in whole if not row.solved) / len(whole)
        if not group:
            print(f"  {floor:>8} {0:>4} {'—':>10} {'—':>11} {'—':>7} {'—':>9} {beyond:>10.0%}")
            continue
        print(
            f"  {floor:>8} {len(group):>4}"
            f" {statistics.fmean(r.avail_mean for r in group):>10.2f}"
            f" {statistics.fmean(r.visibility for r in group):>10.1%}"
            f" {statistics.fmean(r.steps_single for r in group):>7.0%}"
            f" {statistics.fmean(r.mean_cost for r in group):>9.2f}"
            f" {beyond:>10.0%}"
        )

    spreads: tuple[tuple[str, Callable[[Measurement], float]], ...] = (
        ("visibilité", lambda row: row.visibility),
        ("moyenne de coups", lambda row: row.avail_mean),
    )
    for name, pick in spreads:
        print(f"\nSpread de la {name} à indices constants (résolues)")
        print(f"  {'indices':>8} {'min':>7} {'p25':>7} {'médiane':>8} {'p75':>7} {'max':>7}")
        for floor in FLOORS:
            values = sorted(pick(row) for row in solved if row.floor == floor)
            if len(values) < 4:
                continue
            quarters = statistics.quantiles(values, n=4)
            print(
                f"  {floor:>8} {values[0]:>7.3f} {quarters[0]:>7.3f}"
                f" {quarters[1]:>8.3f} {quarters[2]:>7.3f} {values[-1]:>7.3f}"
            )

    print("\nPart des placements par technique (grilles résolues)")
    print(f"  {'indices':>8}", end="")
    for technique in CATALOGUE:
        print(f" {technique.key[:16]:>17}", end="")
    print()
    for floor in FLOORS:
        group = [row for row in solved if row.floor == floor]
        if not group:
            continue
        print(f"  {floor:>8}", end="")
        for technique in CATALOGUE:
            share = statistics.fmean(getattr(row, f"share_{technique.key}") for row in group)
            print(f" {share:>16.0%}", end="")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-floor", type=int, default=50, help="grilles par plancher")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, help="fichier CSV des mesures brutes")
    args = parser.parse_args()

    print(
        f"Échantillon : {len(FLOORS)} planchers de {args.per_floor} grilles",
        file=sys.stderr,
    )
    rows = collect(args.per_floor, args.seed)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0])))
            writer.writeheader()
            writer.writerows(asdict(row) for row in rows)
        print(f"Mesures brutes écrites dans {args.out}", file=sys.stderr)

    summarise(rows)


if __name__ == "__main__":
    main()
