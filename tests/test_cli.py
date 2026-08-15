"""Tests for the command line."""

from pathlib import Path

import pytest
from pypdf import PdfReader
from typer.testing import CliRunner

from sudoku import __version__
from sudoku.cli import app
from sudoku.rating import LEVELS

runner = CliRunner()


def run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, list(args))
    return result.exit_code, result.output


# --- Informational commands -------------------------------------------------


def test_version() -> None:
    code, output = run("version")
    assert code == 0
    assert __version__ in output


def test_niveaux_lists_the_whole_scale() -> None:
    code, output = run("niveaux")
    assert code == 0
    for level in LEVELS:
        assert level.name in output


def test_help_is_offered_when_called_bare() -> None:
    """Bare invocation lists the commands. Click exits 2 on a missing argument."""
    code, output = run()
    assert code == 2
    for command in ("generate", "niveaux", "version"):
        assert command in output


# --- Generating -------------------------------------------------------------


def test_generates_a_pdf(tmp_path: Path) -> None:
    destination = tmp_path / "grilles.pdf"
    code, output = run("generate", "--niveau", "3", "-o", str(destination))
    assert code == 0
    assert destination.exists()
    assert len(PdfReader(destination).pages) == 1
    assert "niveau 3" in output
    assert "Facile" in output


def test_generates_several_grids(tmp_path: Path) -> None:
    destination = tmp_path / "grilles.pdf"
    code, _ = run("generate", "-n", "2", "-c", "4", "-o", str(destination))
    assert code == 0
    assert len(PdfReader(destination).pages) == 4


def test_solutions_are_appended(tmp_path: Path) -> None:
    plain, annotated = tmp_path / "a.pdf", tmp_path / "b.pdf"
    run("generate", "-n", "3", "-c", "2", "-o", str(plain))
    run("generate", "-n", "3", "-c", "2", "-o", str(annotated), "--solutions")
    assert len(PdfReader(annotated).pages) == len(PdfReader(plain).pages) + 1


def test_text_output(tmp_path: Path) -> None:
    destination = tmp_path / "grilles.txt"
    code, _ = run("generate", "-n", "1", "--format", "texte", "-o", str(destination))
    assert code == 0
    assert "┌" in destination.read_text(encoding="utf-8")


def test_the_recap_names_every_grid(tmp_path: Path) -> None:
    destination = tmp_path / "grilles.pdf"
    _, output = run("generate", "-n", "5", "-c", "3", "-o", str(destination))
    assert output.count("indices") == 3
    assert "visibilité" in output


def test_missing_folders_are_created(tmp_path: Path) -> None:
    destination = tmp_path / "a" / "b" / "grilles.pdf"
    code, _ = run("generate", "-n", "1", "-o", str(destination))
    assert code == 0
    assert destination.exists()


def test_default_names_follow_the_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    run("generate", "-n", "1")
    assert (tmp_path / "sudokus.pdf").exists()
    run("generate", "-n", "1", "--format", "texte")
    assert (tmp_path / "sudokus.txt").exists()


# --- Reproducibility --------------------------------------------------------


def test_the_same_seed_replays_the_batch(tmp_path: Path) -> None:
    first = run("generate", "-n", "4", "-c", "2", "--seed", "7", "-o", str(tmp_path / "a.pdf"))[1]
    second = run("generate", "-n", "4", "-c", "2", "--seed", "7", "-o", str(tmp_path / "b.pdf"))[1]
    assert first.replace("a.pdf", "") == second.replace("b.pdf", "")


def test_different_seeds_give_different_batches(tmp_path: Path) -> None:
    first = run("generate", "-n", "4", "--seed", "1", "-o", str(tmp_path / "a.pdf"))[1]
    second = run("generate", "-n", "4", "--seed", "2", "-o", str(tmp_path / "b.pdf"))[1]
    assert first != second


# --- Refusals ---------------------------------------------------------------


@pytest.mark.parametrize("level", ["0", "11", "-3"])
def test_rejects_a_level_off_the_scale(level: str, tmp_path: Path) -> None:
    code, _ = run("generate", "--niveau", level, "-o", str(tmp_path / "x.pdf"))
    assert code != 0


def test_rejects_a_count_below_one(tmp_path: Path) -> None:
    code, _ = run("generate", "-n", "3", "-c", "0", "-o", str(tmp_path / "x.pdf"))
    assert code != 0


def test_rejects_an_unknown_format(tmp_path: Path) -> None:
    code, _ = run("generate", "-n", "3", "--format", "epub", "-o", str(tmp_path / "x.pdf"))
    assert code != 0


def test_the_level_is_required(tmp_path: Path) -> None:
    code, _ = run("generate", "-o", str(tmp_path / "x.pdf"))
    assert code != 0
