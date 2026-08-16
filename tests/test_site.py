"""Tests for what the static site borrows from here.

The site is a second implementation of two things this project already had: the
millimetres of the printed sheet, and the way a booklet climbs. A second
implementation drifts, and the drift is quiet — a sheet an inch narrower still
prints, a booklet that climbs differently still looks like a booklet.

So both are pinned from this side, where the originals live.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from sudoku import __version__
from sudoku.board import CELL_COUNT, SIZE
from sudoku.cli import Bank
from sudoku.rating import LEVELS
from sudoku.render import pdf
from tools import fixtures, metrics, publish

SITE = Path(__file__).resolve().parent.parent / "site"


# --- The sheet, in millimetres ----------------------------------------------


def javascript_constants(path: Path) -> dict[str, Any]:
    """Evaluate the ``export const NAME = …;`` lines of a module.

    The expressions are arithmetic over numbers and names already defined
    above — which is valid Python as well as valid JavaScript, so they are
    evaluated rather than parsed. The names come from a file this project owns.
    """
    values: dict[str, Any] = {}
    source = path.read_text(encoding="utf-8")
    for name, expression in re.findall(r"^export const (\w+) = (.+);$", source, re.MULTILINE):
        values[name] = eval(expression, {"__builtins__": {}}, values)
    return values


@pytest.fixture(scope="module")
def constants() -> dict[str, Any]:
    return javascript_constants(SITE / "js" / "layout.js")


def test_the_site_reads_the_same_page_and_grid(constants: dict[str, Any]) -> None:
    """A sheet that measures anything else is not the sheet already printed."""
    for name in ("PAGE_WIDTH", "PAGE_HEIGHT", "GRID_SIZE", "GRID_LEFT", "GRID_TOP", "GRID_BOTTOM"):
        assert constants[name] == pytest.approx(getattr(pdf, name)), name


def test_the_site_places_the_furniture_where_the_pdf_does(constants: dict[str, Any]) -> None:
    for name in ("HEADLINE_Y", "GAUGE_Y", "NAME_Y", "FOOTER_Y"):
        assert constants[name] == pytest.approx(getattr(pdf, name)), name


def test_the_site_inks_like_the_pdf(constants: dict[str, Any]) -> None:
    assert constants["DIGIT_RATIO"] == pytest.approx(pdf.DIGIT_RATIO)
    assert constants["RULE_GRAY"] == pytest.approx(pdf.RULE_GRAY)
    assert constants["FONT"] == pdf.FONT
    assert constants["FONT_BOLD"] == pdf.FONT_BOLD


def test_the_site_lays_solutions_out_like_the_pdf(constants: dict[str, Any]) -> None:
    assert constants["SOLUTIONS_PER_PAGE"] == pdf.SOLUTIONS_PER_PAGE
    assert constants["SOLUTION_SIZE"] == pytest.approx(pdf.SOLUTION_SIZE)
    assert constants["SOLUTION_COLUMNS"] == pdf.SOLUTION_COLUMNS


def test_the_site_knows_the_shape_of_a_grid_and_the_scale(constants: dict[str, Any]) -> None:
    assert constants["SIZE"] == SIZE
    assert constants["CELL_COUNT"] == CELL_COUNT
    assert constants["LEVEL_COUNT"] == len(LEVELS)


def test_every_constant_of_the_renderer_is_accounted_for(constants: dict[str, Any]) -> None:
    """A constant added to the renderer must reach the site, or be refused here.

    Without this, the drift the other tests catch could simply walk around them
    by arriving under a new name.
    """
    theirs = {
        name
        for name in vars(pdf)
        if name.isupper() and isinstance(vars(pdf)[name], int | float | str)
    }
    assert theirs - set(constants) == set(), "constantes du rendu absentes de layout.js"


# --- The climb ---------------------------------------------------------------


def test_the_ramp_vectors_are_current() -> None:
    """The JavaScript suite checks itself against this file. It must be fresh."""
    frozen = json.loads((SITE / "tests" / "fixtures" / "ramp.json").read_text(encoding="utf-8"))
    assert frozen == fixtures.cases(), "lancer `uv run python tools/fixtures.py`"


# --- The font metrics ---------------------------------------------------------


def test_the_frozen_font_metrics_are_current() -> None:
    """The site centres its own text, so it prints wrong if these go stale."""
    frozen = (SITE / "js" / "metrics.js").read_text(encoding="utf-8")
    assert frozen == metrics.render((pdf.FONT, pdf.FONT_BOLD)), (
        "lancer `uv run python tools/metrics.py`"
    )


# --- The published bank -------------------------------------------------------


def sample_bank(per_level: int = 3, levels: tuple[int, ...] = (1, 2)) -> Bank:
    return {
        "version": __version__,
        "generated": "2026-08-16",
        "seed": 42,
        "levels": [{"number": number, "name": f"Niveau {number}"} for number in levels],
        "puzzles": [
            {
                "id": f"l{level}p{rank}",
                "level": level,
                "givens": 30 + rank,
                "seed": 1000 + rank,
                "puzzle": "." * CELL_COUNT,
                "solution": "1" * CELL_COUNT,
            }
            for level in levels
            for rank in range(per_level)
        ],
    }


def test_the_bank_is_cut_into_chunks_of_the_asked_size(tmp_path: Path) -> None:
    index, _raw, _packed = publish.publish(sample_bank(per_level=7), tmp_path, size=3)
    counts = [chunk["count"] for chunk in index["levels"][0]["chunks"]]
    assert counts == [3, 3, 1]
    assert index["levels"][0]["count"] == 7


def test_a_chunk_holds_grids_and_never_their_answers(tmp_path: Path) -> None:
    """The page the child is looking at must not have the solution in it."""
    publish.publish(sample_bank(), tmp_path)
    chunk = json.loads((tmp_path / "n01-000.json").read_text(encoding="utf-8"))

    assert chunk["level"] == 1
    for entry in chunk["puzzles"]:
        assert set(entry) == {"id", "givens", "seed", "puzzle"}
    assert "solution" not in (tmp_path / "n01-000.json").read_text(encoding="utf-8")


def test_the_answers_sit_in_a_file_of_their_own(tmp_path: Path) -> None:
    publish.publish(sample_bank(), tmp_path)
    solutions = json.loads((tmp_path / "n01-000-sol.json").read_text(encoding="utf-8"))
    chunk = json.loads((tmp_path / "n01-000.json").read_text(encoding="utf-8"))

    assert solutions["level"] == 1
    assert set(solutions["solutions"]) == {entry["id"] for entry in chunk["puzzles"]}
    assert all(len(answer) == CELL_COUNT for answer in solutions["solutions"].values())


def test_the_index_says_everything_the_site_needs(tmp_path: Path) -> None:
    index, _raw, _packed = publish.publish(sample_bank(), tmp_path)
    assert index["version"] == __version__
    assert index["generated"] == "2026-08-16"
    assert index["seed"] == 42
    # Les libellés voyagent, pour que le site n'en code aucun en dur.
    assert [level["name"] for level in index["levels"]] == ["Niveau 1", "Niveau 2"]
    for level in index["levels"]:
        assert sum(chunk["count"] for chunk in level["chunks"]) == level["count"]
        for chunk in level["chunks"]:
            assert (tmp_path / chunk["file"]).exists()


def test_every_grid_of_the_bank_reaches_the_site(tmp_path: Path) -> None:
    bank = sample_bank(per_level=5, levels=(1, 2, 3))
    index, _raw, _packed = publish.publish(bank, tmp_path, size=2)

    published = {
        entry["id"]
        for level in index["levels"]
        for chunk in level["chunks"]
        for entry in json.loads((tmp_path / chunk["file"]).read_text(encoding="utf-8"))["puzzles"]
    }
    assert published == {entry["id"] for entry in bank["puzzles"]}


def test_a_smaller_bank_leaves_no_orphan_behind(tmp_path: Path) -> None:
    """Otherwise files the index no longer mentions stay served, and confuse."""
    publish.publish(sample_bank(per_level=9), tmp_path, size=3)
    assert (tmp_path / "n01-002.json").exists()

    publish._clear(tmp_path)
    publish.publish(sample_bank(per_level=3), tmp_path, size=3)
    assert not (tmp_path / "n01-002.json").exists()
    assert (tmp_path / "n01-000.json").exists()


def test_the_published_bank_matches_its_own_index(tmp_path: Path) -> None:
    index, _raw, _packed = publish.publish(sample_bank(per_level=4), tmp_path, size=3)
    written = {path.name for path in tmp_path.glob("*.json")}
    expected = {"index.json"}
    for level in index["levels"]:
        for chunk in level["chunks"]:
            expected |= {chunk["file"], publish.solutions_name(chunk["file"])}
    assert written == expected
