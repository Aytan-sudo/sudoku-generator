"""Tests for the progressive booklet: the ramp, its cover, and the command."""

from pathlib import Path

import pytest
from pypdf import PdfReader
from typer.testing import CliRunner

from sudoku.cli import app
from sudoku.generator import generate_ramp, ramp
from sudoku.render.base import Cover
from sudoku.render.pdf import PdfRenderer
from sudoku.render.text import TextRenderer

runner = CliRunner()


def run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, list(args))
    return result.exit_code, result.output


# --- The ramp ---------------------------------------------------------------


def test_a_ramp_never_goes_backwards() -> None:
    levels = ramp(3, 6, 20)
    assert levels == sorted(levels)


def test_a_ramp_starts_and_ends_where_asked() -> None:
    levels = ramp(3, 6, 20)
    assert levels[0] == 3
    assert levels[-1] == 6


def test_a_ramp_shares_the_grids_out_evenly() -> None:
    assert ramp(3, 6, 20).count(3) == 5
    assert {ramp(3, 6, 20).count(level) for level in (3, 4, 5, 6)} == {5}


def test_a_remainder_goes_to_the_easier_end() -> None:
    """Better to linger at the start of a booklet than to rush its finish."""
    levels = ramp(1, 4, 10)
    assert levels.count(1) == 3
    assert levels.count(4) == 2


def test_a_ramp_of_one_level_is_flat() -> None:
    assert ramp(5, 5, 6) == [5] * 6


def test_too_few_grids_sample_the_span_instead() -> None:
    assert ramp(1, 10, 3) == [1, 6, 10]
    assert ramp(1, 10, 2) == [1, 10]
    assert ramp(1, 10, 1) == [1]


def test_a_ramp_always_has_the_number_asked_for() -> None:
    for count in range(1, 31):
        assert len(ramp(2, 7, count)) == count


@pytest.mark.parametrize(("start", "end"), [(0, 5), (5, 11), (-1, 3)])
def test_a_ramp_refuses_levels_off_the_scale(start: int, end: int) -> None:
    with pytest.raises(ValueError, match="niveau"):
        ramp(start, end, 10)


def test_a_ramp_refuses_to_go_downhill() -> None:
    with pytest.raises(ValueError, match="dépasse"):
        ramp(6, 3, 10)


def test_a_ramp_refuses_an_empty_booklet() -> None:
    with pytest.raises(ValueError, match="count"):
        ramp(3, 6, 0)


# --- Generating a booklet ---------------------------------------------------


def test_the_booklet_matches_its_ramp() -> None:
    puzzles = generate_ramp(3, 5, 6, seed=5)
    assert [puzzle.rating.level for puzzle in puzzles] == ramp(3, 5, 6)


def test_booklet_grids_are_all_different() -> None:
    puzzles = generate_ramp(2, 4, 9, seed=6)
    assert len({puzzle.board.to_string() for puzzle in puzzles}) == 9


def test_a_booklet_replays_from_its_seed() -> None:
    first = [puzzle.identifier for puzzle in generate_ramp(3, 5, 6, seed=7)]
    second = [puzzle.identifier for puzzle in generate_ramp(3, 5, 6, seed=7)]
    assert first == second


def test_different_seeds_share_no_grid() -> None:
    """Two booklets for two children must have nothing in common."""
    first = {puzzle.board.to_string() for puzzle in generate_ramp(3, 5, 9, seed=111)}
    second = {puzzle.board.to_string() for puzzle in generate_ramp(3, 5, 9, seed=222)}
    assert not first & second


# --- The cover --------------------------------------------------------------


def test_the_cover_adds_one_page(tmp_path: Path) -> None:
    puzzles = generate_ramp(3, 4, 4, seed=8)
    plain, covered = tmp_path / "a.pdf", tmp_path / "b.pdf"
    PdfRenderer().render(puzzles, plain)
    PdfRenderer().render(puzzles, covered, cover=Cover("Carnet", "sous-titre"))
    assert len(PdfReader(covered).pages) == len(PdfReader(plain).pages) + 1


def test_the_cover_carries_its_wording(tmp_path: Path) -> None:
    path = tmp_path / "carnet.pdf"
    PdfRenderer().render(
        generate_ramp(3, 4, 2, seed=9), path, cover=Cover("Carnet d'été", "20 grilles")
    )
    front = PdfReader(path).pages[0].extract_text()
    assert "Carnet d'été" in front
    assert "20 grilles" in front
    assert "Carnet de :" in front


def test_a_cover_without_subtitle_is_fine(tmp_path: Path) -> None:
    path = tmp_path / "carnet.pdf"
    PdfRenderer().render(generate_ramp(3, 4, 2, seed=10), path, cover=Cover("Carnet"))
    assert "Carnet" in PdfReader(path).pages[0].extract_text()


def test_the_text_renderer_takes_a_cover_too(tmp_path: Path) -> None:
    path = tmp_path / "carnet.txt"
    TextRenderer().render(
        generate_ramp(3, 4, 2, seed=11), path, cover=Cover("Carnet", "deux grilles")
    )
    text = path.read_text(encoding="utf-8")
    assert text.startswith("Carnet\ndeux grilles")


# --- The command ------------------------------------------------------------


def test_the_command_builds_a_booklet(tmp_path: Path) -> None:
    path = tmp_path / "carnet.pdf"
    code, output = run("carnet", "--de", "3", "--a", "5", "-c", "6", "--seed", "3", "-o", str(path))
    assert code == 0
    assert len(PdfReader(path).pages) == 1 + 6  # cover, then the grids
    assert "niveaux 3 à 5" in output


def test_the_solutions_are_a_booklet_of_their_own(tmp_path: Path) -> None:
    """What the child gets and what the adult keeps are two documents."""
    path = tmp_path / "carnet.pdf"
    run("carnet", "--de", "3", "--a", "5", "-c", "6", "--seed", "3", "-o", str(path))
    answers = tmp_path / "carnet-solutions.pdf"
    assert answers.exists()
    assert len(PdfReader(answers).pages) == 1
    assert "Solutions" in PdfReader(answers).pages[0].extract_text()


def test_the_solutions_booklet_opens_on_its_content(tmp_path: Path) -> None:
    """No stray blank sheet before the first page of answers."""
    path = tmp_path / "carnet.pdf"
    run("carnet", "--de", "3", "--a", "4", "-c", "8", "--seed", "9", "-o", str(path))
    pages = PdfReader(tmp_path / "carnet-solutions.pdf").pages
    assert len(pages) == 2
    assert "Solutions" in pages[0].extract_text()


def test_the_player_name_appears_on_the_cover(tmp_path: Path) -> None:
    path = tmp_path / "carnet.pdf"
    run("carnet", "--de", "3", "--a", "4", "-c", "4", "-j", "Camille", "-o", str(path))
    reader = PdfReader(path)
    assert "Camille" in reader.pages[0].extract_text()
    assert "Camille" in reader.pages[1].extract_text()


def test_the_recap_counts_each_level(tmp_path: Path) -> None:
    _, output = run(
        "carnet", "--de", "3", "--a", "4", "-c", "4", "--seed", "4", "-o", str(tmp_path / "c.pdf")
    )
    assert "niveau  3" in output
    assert "niveau  4" in output


def test_solutions_can_be_left_out(tmp_path: Path) -> None:
    path = tmp_path / "carnet.pdf"
    code, _ = run("carnet", "--de", "3", "--a", "4", "-c", "4", "--sans-solutions", "-o", str(path))
    assert code == 0
    assert len(PdfReader(path).pages) == 1 + 4
    assert not (tmp_path / "carnet-solutions.pdf").exists()


def test_the_command_refuses_a_downhill_ramp(tmp_path: Path) -> None:
    code, _ = run("carnet", "--de", "6", "--a", "3", "-o", str(tmp_path / "c.pdf"))
    assert code == 1


def test_the_default_booklet_is_named_carnet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    run("carnet", "--de", "3", "--a", "4", "-c", "4", "--seed", "12", "--joueur", "Zoé")
    names = {path.name for path in tmp_path.iterdir()}
    assert len(names) == 2
    assert all(name.startswith("carnet-zoe-") and "12" in name for name in names)
    assert sum(name.endswith("-solutions.pdf") for name in names) == 1
