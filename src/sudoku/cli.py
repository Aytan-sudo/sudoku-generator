"""Command line entry point.

Options and messages are in French, like the sheets themselves — whoever runs
this is the person handing the grids over. Command names stay ASCII so they can
be typed without fighting a keyboard layout.
"""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from sudoku import __version__
from sudoku.generator import (
    GIVENS_TARGET,
    GenerationError,
    Puzzle,
    generate_many,
    generate_ramp,
)
from sudoku.rating import BY_NUMBER, LEVELS
from sudoku.render.base import Cover, Renderer
from sudoku.render.pdf import PdfRenderer
from sudoku.render.text import TextRenderer

app = typer.Typer(
    help="Générateur de sudokus avec classificateur de difficulté et rendu PDF A4.",
    no_args_is_help=True,
    add_completion=False,
)


class Format(StrEnum):
    """Output formats on offer."""

    pdf = "pdf"
    texte = "texte"


DEFAULT_NAME = {Format.pdf: Path("sudokus.pdf"), Format.texte: Path("sudokus.txt")}
RENDERERS: dict[Format, type[Renderer]] = {Format.pdf: PdfRenderer, Format.texte: TextRenderer}


@app.callback()
def main() -> None:
    """Générateur de sudokus."""


@app.command()
def version() -> None:
    """Affiche la version installée."""
    typer.echo(f"sudoku-generator {__version__}")


@app.command()
def niveaux() -> None:
    """Décrit l'échelle de difficulté, de 1 à 10."""
    typer.secho(f"{'niv':>4}  {'nom':<14}  indices", bold=True)
    for level in LEVELS:
        low, high = GIVENS_TARGET[level.number]
        typer.echo(f"{level.number:>4}  {level.name:<14}  {low}-{high}")


@app.command()
def generate(
    niveau: Annotated[
        int,
        typer.Option("--niveau", "-n", min=1, max=len(LEVELS), help="Difficulté visée, de 1 à 10."),
    ],
    nombre: Annotated[
        int, typer.Option("--nombre", "-c", min=1, help="Nombre de grilles à produire.")
    ] = 1,
    sortie: Annotated[Path | None, typer.Option("--out", "-o", help="Fichier à écrire.")] = None,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Rend le tirage reproductible. Tirée au hasard si omise."),
    ] = None,
    solutions: Annotated[
        bool,
        typer.Option("--solutions/--sans-solutions", help="Ajoute les solutions à la fin."),
    ] = False,
    format_: Annotated[Format, typer.Option("--format", help="Format de sortie.")] = Format.pdf,
) -> None:
    """Produit des grilles d'un niveau donné.

    Chaque grille porte sa propre seed en pied de page : elle peut être
    régénérée seule, indépendamment du lot.
    """
    destination = sortie or DEFAULT_NAME[format_]

    try:
        puzzles = generate_many(niveau, nombre, seed)
    except GenerationError as error:
        typer.secho(f"Échec de génération : {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error

    destination.parent.mkdir(parents=True, exist_ok=True)
    RENDERERS[format_]().render(puzzles, destination, solutions=solutions)

    _report(puzzles, niveau, destination)


@app.command()
def carnet(
    de: Annotated[
        int, typer.Option("--de", min=1, max=len(LEVELS), help="Niveau de la première grille.")
    ] = 3,
    a: Annotated[
        int, typer.Option("--a", min=1, max=len(LEVELS), help="Niveau de la dernière grille.")
    ] = 6,
    nombre: Annotated[
        int, typer.Option("--nombre", "-c", min=1, help="Nombre de grilles du carnet.")
    ] = 20,
    sortie: Annotated[Path | None, typer.Option("--out", "-o", help="Fichier à écrire.")] = None,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Rend le tirage reproductible. Tirée au hasard si omise."),
    ] = None,
    titre: Annotated[
        str, typer.Option("--titre", help="Titre de la page de garde.")
    ] = "Carnet de sudokus",
    solutions: Annotated[
        bool,
        typer.Option("--solutions/--sans-solutions", help="Ajoute les solutions à la fin."),
    ] = True,
    format_: Annotated[Format, typer.Option("--format", help="Format de sortie.")] = Format.pdf,
) -> None:
    """Produit un carnet dont la difficulté monte de page en page.

    Les premières grilles mettent en confiance, les dernières font travailler.
    """
    if de > a:
        typer.secho(
            f"Le niveau de départ ({de}) dépasse celui d'arrivée ({a}).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    destination = sortie or DEFAULT_NAME[format_].with_stem("carnet")

    try:
        puzzles = generate_ramp(de, a, nombre, seed)
    except GenerationError as error:
        typer.secho(f"Échec de génération : {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error

    cover = Cover(
        title=titre,
        subtitle=f"{nombre} grilles, du niveau {de} « {BY_NUMBER[de].name} »"
        f" au niveau {a} « {BY_NUMBER[a].name} »",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    RENDERERS[format_]().render(puzzles, destination, solutions=solutions, cover=cover)

    typer.secho(f"{len(puzzles)} grilles, niveaux {de} à {a} → {destination}", bold=True)
    counts = Counter(puzzle.rating.level for puzzle in puzzles)
    for level in sorted(counts):
        typer.echo(
            f"  niveau {level:>2} « {BY_NUMBER[level].name:<14} » {counts[level]:>3} grilles"
        )
    typer.echo(f"  seed du carnet : {seed if seed is not None else 'tirée au hasard'}")


def _report(puzzles: list[Puzzle], level: int, destination: Path) -> None:
    """Recap what was produced, so a batch can be judged without opening it."""
    plural = "s" if len(puzzles) > 1 else ""
    typer.secho(
        f"{len(puzzles)} grille{plural} de niveau {level} « {BY_NUMBER[level].name} »"
        f" → {destination}",
        bold=True,
    )
    for puzzle in puzzles:
        rating = puzzle.rating
        typer.echo(
            f"  n° {puzzle.identifier}   {rating.givens} indices"
            f"   visibilité {rating.visibility:.0%}   seed {puzzle.seed}"
        )


if __name__ == "__main__":
    app()
