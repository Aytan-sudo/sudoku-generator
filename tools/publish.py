"""Cut an exported bank into what a browser can actually fetch.

``sudoku export`` writes one file holding everything, which is the right shape
for a contract and the wrong one for a site: a child printing a single level-3
grid would download all ten levels, solutions included. So the bank is split
twice over.

**By level, then by chunk**, so the cost of a first print stops growing with the
bank. A chunk of 500 grids weighs about 24 Ko gzipped whether the bank holds
5 000 or 200 000 — the site reads the index, picks one chunk, and draws from it.

**Puzzles apart from solutions**, so the page the child is looking at never held
the answer. The solutions sit in a file of their own, fetched only when an adult
asks to print them. Nothing here is secret — everything served is public — but
the answer is no longer one keystroke away from the grid.

    uv run python tools/publish.py out/banque-20k.json

Measured on a bank of 500: splitting the solutions off halves what the first
fetch costs, 45 Ko gzipped down to 24. Packing the two boards into one (a
solution plus a bitmask of the givens) was tried and dropped — base64 looks like
noise to gzip, and it came out worse than the plain digits it replaced.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import TypedDict

from sudoku import __version__
from sudoku.cli import Bank

CHUNK_SIZE = 500
"""Grids per file. Small enough that one is a cheap download, large enough that
the index does not turn into a directory listing."""

SITE_BANK = Path("site/banque")

CHUNK_GLOB = "n[0-9][0-9]-*.json"
"""What this script considers its own, and may therefore delete."""


class SitePuzzle(TypedDict):
    """One grid, minus what the file it lives in already says.

    The level is dropped — a chunk holds a single level — but ``givens`` and
    ``seed`` stay: the printed footer shows them, exactly as the PDF does.
    """

    id: str
    givens: int
    seed: int
    puzzle: str


class PuzzleChunk(TypedDict):
    level: int
    puzzles: list[SitePuzzle]


class SolutionChunk(TypedDict):
    """Solutions by identifier, so nothing depends on two files staying in step."""

    level: int
    solutions: dict[str, str]


class SiteChunk(TypedDict):
    file: str
    count: int


class SiteLevel(TypedDict):
    number: int
    name: str
    count: int
    chunks: list[SiteChunk]


class SiteIndex(TypedDict):
    """The only file the site loads before it can do anything.

    It carries the level names so the site hardcodes no French wording, and the
    generator version so a stale bank can be spotted from the page footer.
    """

    version: str
    generated: str
    seed: int
    levels: list[SiteLevel]


def chunk_stem(level: int, position: int) -> str:
    """``n03-002`` — sorts naturally, and says what it holds at a glance."""
    return f"n{level:02d}-{position:03d}"


def solutions_name(file: str) -> str:
    """The answers that go with a chunk. Mirrored by ``solutionsFile`` in bank.js."""
    return file.replace(".json", "-sol.json")


def _write(path: Path, payload: object) -> tuple[int, int]:
    """Write compact JSON, and report what it costs raw and over the wire."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(data)
    return len(data), len(gzip.compress(data, 9))


def _clear(directory: Path) -> int:
    """Remove the chunks of a previous run.

    A smaller bank than last time would otherwise leave files behind that the
    index no longer mentions — served, unreachable, and confusing. Only files
    matching this script's own naming are touched.
    """
    stale = sorted(directory.glob(CHUNK_GLOB))
    for path in stale:
        path.unlink()
    return len(stale)


def publish(bank: Bank, directory: Path, size: int = CHUNK_SIZE) -> tuple[SiteIndex, int, int]:
    """Write the index and every chunk under ``directory``. Returns totals in bytes."""
    directory.mkdir(parents=True, exist_ok=True)
    names = {level["number"]: level["name"] for level in bank["levels"]}

    by_level: dict[int, list[SitePuzzle]] = {}
    solutions: dict[int, dict[str, str]] = {}
    for entry in bank["puzzles"]:
        level = entry["level"]
        by_level.setdefault(level, []).append(
            {
                "id": entry["id"],
                "givens": entry["givens"],
                "seed": entry["seed"],
                "puzzle": entry["puzzle"],
            }
        )
        solutions.setdefault(level, {})[entry["id"]] = entry["solution"]

    levels: list[SiteLevel] = []
    total_raw = total_gzip = 0

    for level in sorted(by_level):
        puzzles = by_level[level]
        chunks: list[SiteChunk] = []

        for position, start in enumerate(range(0, len(puzzles), size)):
            batch = puzzles[start : start + size]
            name = f"{chunk_stem(level, position)}.json"

            puzzle_chunk: PuzzleChunk = {"level": level, "puzzles": batch}
            raw, packed = _write(directory / name, puzzle_chunk)
            total_raw += raw
            total_gzip += packed

            solution_chunk: SolutionChunk = {
                "level": level,
                "solutions": {entry["id"]: solutions[level][entry["id"]] for entry in batch},
            }
            raw, packed = _write(directory / solutions_name(name), solution_chunk)
            total_raw += raw
            total_gzip += packed

            chunks.append({"file": name, "count": len(batch)})

        levels.append(
            {
                "number": level,
                "name": names.get(level, f"Niveau {level}"),
                "count": len(puzzles),
                "chunks": chunks,
            }
        )

    index: SiteIndex = {
        "version": bank["version"],
        "generated": bank["generated"],
        "seed": bank["seed"],
        "levels": levels,
    }
    raw, packed = _write(directory / "index.json", index)
    return index, total_raw + raw, total_gzip + packed


def _report(index: SiteIndex, directory: Path, raw: int, packed: int) -> None:
    for level in index["levels"]:
        first = directory / level["chunks"][0]["file"]
        weight = len(gzip.compress(first.read_bytes(), 9)) / 1024
        print(
            f"  niveau {level['number']:>2} « {level['name']:<14} »"
            f" {level['count']:>6} grilles"
            f"  {len(level['chunks']):>3} paquets"
            f"  {weight:>5.0f} Ko gzip le paquet"
        )

    entry = (directory / "index.json").stat().st_size
    smallest = min(
        len(gzip.compress((directory / level["chunks"][0]["file"]).read_bytes(), 9))
        for level in index["levels"]
    )
    print(
        f"\n{raw / 1024 / 1024:.1f} Mo au total, {packed / 1024 / 1024:.1f} Mo gzip"
        f"\nPremière impression : {entry / 1024:.0f} Ko d'index"
        f" + {smallest / 1024:.0f} Ko de paquet, quelle que soit la taille de la banque."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Découpe une banque exportée pour le site.")
    parser.add_argument("banque", type=Path, help="Banque JSON écrite par `sudoku export`.")
    parser.add_argument("--dossier", type=Path, default=SITE_BANK, help="Dossier de sortie.")
    parser.add_argument("--paquet", type=int, default=CHUNK_SIZE, help="Grilles par fichier.")
    args = parser.parse_args()

    if args.paquet < 1:
        parser.error("--paquet doit valoir au moins 1")

    bank: Bank = json.loads(args.banque.read_text(encoding="utf-8"))
    if bank["version"] != __version__:
        print(
            f"Attention : banque produite par la version {bank['version']},"
            f" générateur installé en {__version__}.",
            file=sys.stderr,
        )

    removed = _clear(args.dossier) if args.dossier.exists() else 0
    if removed:
        print(f"{removed} fichiers du tirage précédent retirés.")

    index, raw, packed = publish(bank, args.dossier, args.paquet)
    print(f"{len(bank['puzzles'])} grilles → {args.dossier}")
    _report(index, args.dossier, raw, packed)


if __name__ == "__main__":
    main()
