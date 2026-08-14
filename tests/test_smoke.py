"""Smoke tests: the package imports and the CLI is reachable."""

from typer.testing import CliRunner

from sudoku import __version__
from sudoku.cli import app


def test_version_is_set() -> None:
    assert __version__


def test_cli_version_command() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
