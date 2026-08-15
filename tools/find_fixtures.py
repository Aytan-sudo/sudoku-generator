"""Find, for each technique, a grid that genuinely requires it.

Hand-building a grid where an X-Wing is the one thing standing between you and
the solution is painful and error-prone. Searching for one is neither: dig grids
at random, run the human solver, and keep the first whose ceiling is the wanted
technique. That the search succeeds for every entry of the catalogue is itself
worth knowing — it means no technique is redundant, and the ordering by cost is
consistent with what grids actually demand.

    uv run python tools/find_fixtures.py

Prints the grids as ready-to-paste source. They are frozen into tests/grids.py
rather than searched for at test time, so the suite stays fast and deterministic.
"""

from __future__ import annotations

import argparse
import random
import sys

from sudoku.generator import dig
from sudoku.human import solve_logically
from sudoku.solver import complete_grid
from sudoku.techniques import CATALOGUE

FLOORS = (26, 28, 30, 32)
"""Given counts worth digging to — where the advanced techniques start to bite."""


def search(keys: set[str], seed: int, attempts: int) -> dict[str, str]:
    """Dig until every key in ``keys`` has a grid whose ceiling is that technique."""
    rng = random.Random(seed)
    found: dict[str, str] = {}

    for attempt in range(attempts):
        if not keys - found.keys():
            break
        board = dig(complete_grid(rng), rng, rng.choice(FLOORS))
        log = solve_logically(board)
        if not log.solved or log.ceiling is None:
            continue
        if log.ceiling.key in keys and log.ceiling.key not in found:
            found[log.ceiling.key] = board.to_string()
            print(
                f"  {log.ceiling.key:<18} {board.givens} indices (essai {attempt + 1})",
                file=sys.stderr,
                flush=True,
            )
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260815)
    parser.add_argument("--attempts", type=int, default=40_000)
    parser.add_argument(
        "--from-cost",
        type=int,
        default=50,
        help="Ne chercher que pour les techniques à partir de ce coût.",
    )
    args = parser.parse_args()

    wanted = [technique for technique in CATALOGUE if technique.cost >= args.from_cost]
    found = search({technique.key for technique in wanted}, args.seed, args.attempts)

    missing = [technique.key for technique in wanted if technique.key not in found]
    if missing:
        print(f"\nIntrouvables : {', '.join(missing)}", file=sys.stderr)

    print("NEEDS_TECHNIQUE: dict[str, str] = {")
    for technique in wanted:
        grid = found.get(technique.key)
        if grid is None:
            continue
        rows = "\n".join("    " + grid[start : start + 9] for start in range(0, 81, 9))
        print(f'    "{technique.key}": compact("""\n{rows}\n    """),')
    print("}")

    raise SystemExit(1 if missing else 0)


if __name__ == "__main__":
    main()
