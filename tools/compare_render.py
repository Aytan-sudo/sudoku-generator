"""Confront the site's renderer with this one, pixel by pixel.

The sheet is drawn twice: by ReportLab here, and by two hundred lines of
JavaScript in ``site/js/``. Tests can check that both place a 180 mm square at
15 mm from the edge; they cannot check that the result *looks* like the booklets
already printed. This can — it renders the same puzzle through both and counts
the pixels that differ.

    uv run python tools/compare_render.py

Needs Node and Poppler's ``pdftoppm``, which is why it is a script and not a
test: the suite that runs on every push has no business requiring either.

A handful of pixels apart is expected and harmless — the circles of the gauge
are four Bézier curves on one side and a true arc on the other, so their
antialiasing differs by a shade. Anything structural shows up as thousands.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from sudoku.board import Board
from sudoku.generator import Puzzle
from sudoku.human import solve_logically
from sudoku.rating import rate
from sudoku.render.base import Cover
from sudoku.render.pdf import PdfRenderer

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

TODAY = date(2026, 8, 16)
PLAYER = "Louane"
COVER = Cover(title="Carnet de sudokus", subtitle="Comparaison des deux rendus")

TOLERANCE = 32
"""Écart d'intensité, sur 255, en deçà duquel deux pixels sont dits identiques."""

SCRIPT = """
import { readFileSync, writeFileSync } from "node:fs";
import { render, renderSolutions } from "%(site)s/js/sheet.js";

const puzzles = JSON.parse(readFileSync("%(input)s", "utf8"));
const today = new Date(2026, 7, 16);
const cover = { title: %(title)s, subtitle: %(subtitle)s };
writeFileSync("%(grids)s", render(puzzles, { cover, player: %(player)s, today }));
writeFileSync("%(answers)s", renderSolutions(puzzles));
"""


def read_pgm(path: Path) -> tuple[int, int, bytes]:
    """Width, height and pixels of a binary PGM — Poppler's grayscale output."""
    data = path.read_bytes()
    fields: list[int] = []
    position = 2
    while len(fields) < 3:
        while data[position : position + 1].isspace():
            position += 1
        if data[position : position + 1] == b"#":
            while data[position : position + 1] != b"\n":
                position += 1
            continue
        start = position
        while not data[position : position + 1].isspace():
            position += 1
        fields.append(int(data[start:position]))
    return fields[0], fields[1], data[position + 1 :]


def sample(count: int) -> list[Puzzle]:
    """One puzzle per level, taken from the bank the site actually serves."""
    index = json.loads((SITE / "banque" / "index.json").read_text(encoding="utf-8"))
    puzzles: list[Puzzle] = []

    for level in index["levels"][:count]:
        name = level["chunks"][0]["file"]
        chunk = json.loads((SITE / "banque" / name).read_text(encoding="utf-8"))
        answers = json.loads(
            (SITE / "banque" / name.replace(".json", "-sol.json")).read_text(encoding="utf-8")
        )
        entry = chunk["puzzles"][0]
        board = Board.from_string(entry["puzzle"])
        puzzles.append(
            Puzzle(
                board=board,
                solution=Board.from_string(answers["solutions"][entry["id"]]),
                rating=rate(board, solve_logically(board)),
                seed=entry["seed"],
            )
        )
    return puzzles


def as_site_json(puzzles: list[Puzzle], names: dict[int, str]) -> str:
    return json.dumps(
        [
            {
                "id": puzzle.identifier,
                "level": puzzle.rating.level,
                "levelName": names[puzzle.rating.level],
                "givens": puzzle.board.givens,
                "seed": puzzle.seed,
                "puzzle": puzzle.board.to_string(),
                "solution": puzzle.solution.to_string(),
            }
            for puzzle in puzzles
        ]
    )


def rasterise(pdf: Path, page: int, folder: Path, resolution: int) -> Path:
    prefix = folder / f"{pdf.stem}-{page}"
    subprocess.run(
        [
            "pdftoppm",
            "-r",
            str(resolution),
            "-gray",
            "-f",
            str(page),
            "-l",
            str(page),
            str(pdf),
            str(prefix),
        ],
        check=True,
        capture_output=True,
    )
    pages = sorted(folder.glob(f"{prefix.name}-*.pgm"))
    if not pages:
        raise RuntimeError(f"pdftoppm n'a rien écrit pour {pdf} page {page}")
    return pages[0]


def compare(left: Path, right: Path, resolution: int, folder: Path, page: int) -> tuple[int, int]:
    """Pixels that differ beyond tolerance, and the worst gap seen."""
    width, height, mine = read_pgm(rasterise(left, page, folder, resolution))
    other_width, other_height, theirs = read_pgm(rasterise(right, page, folder, resolution))
    if (width, height) != (other_width, other_height):
        raise RuntimeError(
            f"pages de tailles différentes : {width}x{height} / {other_width}x{other_height}"
        )

    gaps = [abs(a - b) for a, b in zip(mine, theirs, strict=True)]
    return sum(1 for gap in gaps if gap > TOLERANCE), max(gaps)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--niveaux", type=int, default=3, help="Nombre de niveaux comparés.")
    parser.add_argument("--resolution", type=int, default=100, help="Points par pouce.")
    args = parser.parse_args()

    puzzles = sample(args.niveaux)
    index = json.loads((SITE / "banque" / "index.json").read_text(encoding="utf-8"))
    names = {level["number"]: level["name"] for level in index["levels"]}

    with tempfile.TemporaryDirectory() as raw:
        folder = Path(raw)
        (folder / "puzzles.json").write_text(as_site_json(puzzles, names), encoding="utf-8")

        script = SCRIPT % {
            "site": SITE,
            "input": folder / "puzzles.json",
            "grids": folder / "site.pdf",
            "answers": folder / "site-solutions.pdf",
            "title": json.dumps(COVER.title),
            "subtitle": json.dumps(COVER.subtitle),
            "player": json.dumps(PLAYER),
        }
        (folder / "run.mjs").write_text(script, encoding="utf-8")
        subprocess.run(["node", str(folder / "run.mjs")], check=True)

        renderer = PdfRenderer(today=TODAY)
        renderer.render(puzzles, folder / "python.pdf", cover=COVER, player=PLAYER)
        renderer.render_solutions(puzzles, folder / "python-solutions.pdf")

        worst = 0
        for label, mine, theirs, pages in (
            ("garde", "site.pdf", "python.pdf", [1]),
            ("grilles", "site.pdf", "python.pdf", list(range(2, len(puzzles) + 2))),
            ("solutions", "site-solutions.pdf", "python-solutions.pdf", [1]),
        ):
            for page in pages:
                differing, gap = compare(
                    folder / mine, folder / theirs, args.resolution, folder, page
                )
                worst = max(worst, differing)
                verdict = "identique" if differing == 0 else f"{differing} pixels d'écart"
                print(f"  {label:<10} page {page:<2} {verdict}  (écart max {gap}/255)")

    if worst:
        print(f"\nLes deux rendus divergent : {worst} pixels au pire.", file=sys.stderr)
        raise SystemExit(1)
    print("\nLes deux rendus coïncident.")


if __name__ == "__main__":
    main()
