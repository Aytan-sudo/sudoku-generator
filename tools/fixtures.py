"""Freeze what the JavaScript port has to reproduce.

The site tires its own booklets, so ``generator.ramp()`` exists twice: once here
and once in ``site/js/draw.js``. Two implementations of one rule drift, and the
drift is silent — a booklet that climbs slightly differently looks fine.

So the rule is pinned. This writes the answers the Python gives; the JavaScript
suite reads the same file and must give them back; and ``tests/test_site.py``
regenerates it to make sure nobody changed the rule without changing the file.

    uv run python tools/fixtures.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TypedDict

from sudoku.generator import ramp

TARGET = Path("site/tests/fixtures/ramp.json")

CASES: tuple[tuple[int, int, int], ...] = (
    # Moins de grilles que de niveaux : l'intervalle est échantillonné.
    (1, 10, 1),
    (1, 10, 2),
    (1, 10, 3),
    (1, 10, 10),
    (3, 6, 2),
    (2, 9, 5),
    # Plus de grilles que de niveaux : les parts, et le reste vers le bas.
    (3, 6, 20),
    (1, 10, 25),
    (1, 3, 7),
    (2, 4, 10),
    (7, 9, 100),
    # Un seul niveau, et le carnet d'une page.
    (5, 5, 4),
    (1, 1, 1),
)


class Case(TypedDict):
    start: int
    end: int
    count: int
    levels: list[int]


def cases() -> list[Case]:
    return [
        {"start": start, "end": end, "count": count, "levels": ramp(start, end, count)}
        for start, end, count in CASES
    ]


def render() -> str:
    return json.dumps(cases(), indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Écrit les vecteurs de test partagés.")
    parser.add_argument("--out", type=Path, default=TARGET)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(), encoding="utf-8")
    print(f"{args.out} écrit — {len(CASES)} cas.")


if __name__ == "__main__":
    main()
