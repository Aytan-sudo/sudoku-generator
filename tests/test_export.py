"""Tests for the JSON bank exported for a static site."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sudoku import __version__
from sudoku.board import CELL_COUNT, Board
from sudoku.cli import Bank, app
from sudoku.rating import LEVELS
from sudoku.solver import has_unique_solution

runner = CliRunner()


def run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, list(args))
    return result.exit_code, result.output


@pytest.fixture(scope="module")
def bank(tmp_path_factory: pytest.TempPathFactory) -> Bank:
    path = tmp_path_factory.mktemp("bank") / "banque.json"
    code, _ = run("export", "--de", "2", "--a", "4", "-c", "3", "--seed", "5", "-o", str(path))
    assert code == 0
    loaded: Bank = json.loads(path.read_text(encoding="utf-8"))
    return loaded


# --- Shape ------------------------------------------------------------------


def test_the_bank_says_where_it_came_from(bank: Bank) -> None:
    """A site serving these needs to know what produced them."""
    assert bank["version"] == __version__
    assert bank["seed"] == 5
    assert len(bank["generated"]) == len("2026-08-16")


def test_level_names_travel_with_the_puzzles(bank: Bank) -> None:
    """So the site never has to hardcode the French wording."""
    assert [level["number"] for level in bank["levels"]] == [2, 3, 4]
    names = {level["name"] for level in bank["levels"]}
    assert names <= {level.name for level in LEVELS}


def test_one_entry_per_grid_asked_for(bank: Bank) -> None:
    assert len(bank["puzzles"]) == 9


def test_each_entry_carries_what_a_site_needs(bank: Bank) -> None:
    for entry in bank["puzzles"]:
        assert set(entry) == {"id", "level", "givens", "seed", "puzzle", "solution"}
        assert len(entry["id"]) == 8
        assert len(entry["puzzle"]) == CELL_COUNT
        assert len(entry["solution"]) == CELL_COUNT


# --- Contents -----------------------------------------------------------------


def test_the_levels_are_the_ones_requested(bank: Bank) -> None:
    assert {entry["level"] for entry in bank["puzzles"]} == {2, 3, 4}


def test_every_exported_grid_is_a_proper_puzzle(bank: Bank) -> None:
    for entry in bank["puzzles"]:
        assert has_unique_solution(Board.from_string(entry["puzzle"]))


def test_the_stored_solution_solves_the_grid(bank: Bank) -> None:
    for entry in bank["puzzles"]:
        board = Board.from_string(entry["puzzle"])
        solution = Board.from_string(entry["solution"])
        assert solution.is_solved()
        for index in range(CELL_COUNT):
            if board[index]:
                assert board[index] == solution[index]


def test_the_given_count_matches_the_grid(bank: Bank) -> None:
    for entry in bank["puzzles"]:
        assert Board.from_string(entry["puzzle"]).givens == entry["givens"]


def test_grids_are_all_distinct(bank: Bank) -> None:
    assert len({entry["puzzle"] for entry in bank["puzzles"]}) == len(bank["puzzles"])


# --- The command ------------------------------------------------------------


def test_the_same_seed_exports_the_same_bank(tmp_path: Path) -> None:
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    run("export", "--de", "3", "--a", "3", "-c", "2", "--seed", "9", "-o", str(first))
    run("export", "--de", "3", "--a", "3", "-c", "2", "--seed", "9", "-o", str(second))
    assert json.loads(first.read_text())["puzzles"] == json.loads(second.read_text())["puzzles"]


def test_compact_by_default_and_indented_on_request(tmp_path: Path) -> None:
    compact, pretty = tmp_path / "a.json", tmp_path / "b.json"
    run("export", "--de", "3", "--a", "3", "-c", "2", "--seed", "9", "-o", str(compact))
    run("export", "--de", "3", "--a", "3", "-c", "2", "--seed", "9", "--lisible", "-o", str(pretty))
    assert pretty.stat().st_size > compact.stat().st_size
    assert "\n" not in compact.read_text(encoding="utf-8")


def test_the_default_name_marks_it_as_a_bank(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    run("export", "--de", "5", "--a", "5", "-c", "2", "--seed", "3")
    name = next((tmp_path / "out").iterdir()).name
    assert name.startswith("banque-")
    assert name.endswith(".json")


def test_a_downhill_range_is_refused(tmp_path: Path) -> None:
    code, _ = run("export", "--de", "6", "--a", "3", "-o", str(tmp_path / "x.json"))
    assert code == 1
