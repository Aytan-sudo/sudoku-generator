"""Command line entry point.

Placeholder: only ``--version`` is wired up so far, so that the toolchain can be
verified end to end. Commands are added from step 6 of ROADMAP.md onwards.
"""

import typer

from sudoku import __version__

app = typer.Typer(
    help="Générateur de sudokus avec classificateur de difficulté et rendu PDF A4.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Point d'entrée. Les sous-commandes sont ajoutées à l'étape 6."""


@app.command()
def version() -> None:
    """Affiche la version installée."""
    typer.echo(f"sudoku-generator {__version__}")


if __name__ == "__main__":
    app()
