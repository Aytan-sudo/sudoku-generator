"""Command line entry point.

Options and messages are in French, like the sheets themselves — whoever runs
this is the person handing the grids over. Command names stay ASCII so they can
be typed without fighting a keyboard layout.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import unicodedata
from collections import Counter
from collections.abc import Sequence
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Annotated, TypedDict

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


SUFFIX = {Format.pdf: ".pdf", Format.texte: ".txt"}
RENDERERS: dict[Format, type[Renderer]] = {Format.pdf: PdfRenderer, Format.texte: TextRenderer}


class ExportedLevel(TypedDict):
    """One rung, as a consumer of the bank sees it."""

    number: int
    name: str


class ExportedPuzzle(TypedDict):
    """One grid. Both boards are 81 characters, dots for the empty cells."""

    id: str
    level: int
    givens: int
    seed: int
    puzzle: str
    solution: str


class Bank(TypedDict):
    """What `sudoku export` writes.

    Named and typed because it is a contract with whatever consumes it — a
    static site has no way to ask the generator what it meant.
    """

    version: str
    generated: str
    seed: int
    levels: list[ExportedLevel]
    puzzles: list[ExportedPuzzle]


OUTPUT_DIR = Path("out")
"""Where generated files land unless told otherwise.

Keeping them out of the project root matters more than it looks: they are build
output, git ignores them, and nothing but the seed can bring one back once it is
gone. A folder of their own makes that plain.
"""


def _slug(text: str) -> str:
    """Reduce a name to something safe in a filename, accents included."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    kept = "".join(char if char.isalnum() else "-" for char in plain.lower())
    return "-".join(part for part in kept.split("-") if part)


def _default_path(
    prefix: str,
    player: str | None,
    seed: int,
    puzzles: Sequence[Puzzle],
    suffix: str,
) -> Path:
    """Build a name no earlier run can collide with.

    Date and seed say where a file came from; the trailing tag is a digest of the
    grids themselves. So the same command run twice lands on the same name and
    overwrites an identical file, while anything that differs gets its own —
    which is what keeps a folder of test booklets readable.
    """
    digest = "".join(puzzle.identifier for puzzle in puzzles).encode()
    tag = hashlib.blake2b(digest, digest_size=4).hexdigest()
    parts = [prefix]
    if player:
        parts.append(_slug(player))
    parts += [f"{date.today():%Y%m%d}", str(seed), tag]
    return Path("-".join(parts) + suffix)


def _beside(path: Path, marker: str) -> Path:
    """A companion file next to ``path``, e.g. carnet.pdf → carnet-solutions.pdf."""
    return path.with_name(f"{path.stem}-{marker}{path.suffix}")


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
    joueur: Annotated[
        str | None, typer.Option("--joueur", "-j", help="Nom inscrit sur les feuilles.")
    ] = None,
    sortie: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Fichier précis à écrire, dossier compris."),
    ] = None,
    dossier: Annotated[
        Path, typer.Option("--dossier", "-d", help="Dossier de sortie.")
    ] = OUTPUT_DIR,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Rend le tirage reproductible. Tirée au hasard si omise."),
    ] = None,
    solutions: Annotated[
        bool,
        typer.Option("--solutions/--sans-solutions", help="Écrit aussi un fichier de solutions."),
    ] = False,
    format_: Annotated[Format, typer.Option("--format", help="Format de sortie.")] = Format.pdf,
) -> None:
    """Produit des grilles d'un niveau donné.

    Chaque grille porte sa propre seed en pied de page : elle peut être
    régénérée seule, indépendamment du lot.
    """
    if seed is None:
        seed = secrets.randbits(32)

    try:
        puzzles = generate_many(niveau, nombre, seed)
    except GenerationError as error:
        typer.secho(f"Échec de génération : {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error

    destination = sortie or dossier / _default_path(
        "sudokus", joueur, seed, puzzles, SUFFIX[format_]
    )
    _write(puzzles, destination, format_, solutions=solutions, player=joueur)

    plural = "s" if len(puzzles) > 1 else ""
    typer.secho(
        f"{len(puzzles)} grille{plural} de niveau {niveau} « {BY_NUMBER[niveau].name} »"
        f" → {destination}",
        bold=True,
    )
    for puzzle in puzzles:
        rating = puzzle.rating
        typer.echo(
            f"  n° {puzzle.identifier}   {rating.givens} indices"
            f"   visibilité {rating.visibility:.0%}   seed {puzzle.seed}"
        )
    _announce_solutions(solutions, destination)


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
    joueur: Annotated[
        str | None, typer.Option("--joueur", "-j", help="Nom inscrit sur la garde et les feuilles.")
    ] = None,
    sortie: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Fichier précis à écrire, dossier compris."),
    ] = None,
    dossier: Annotated[
        Path, typer.Option("--dossier", "-d", help="Dossier de sortie.")
    ] = OUTPUT_DIR,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Rend le tirage reproductible. Tirée au hasard si omise."),
    ] = None,
    titre: Annotated[
        str, typer.Option("--titre", help="Titre de la page de garde.")
    ] = "Carnet de sudokus",
    solutions: Annotated[
        bool,
        typer.Option("--solutions/--sans-solutions", help="Écrit aussi un carnet de solutions."),
    ] = True,
    format_: Annotated[Format, typer.Option("--format", help="Format de sortie.")] = Format.pdf,
) -> None:
    """Produit un carnet dont la difficulté monte de page en page.

    Les premières grilles mettent en confiance, les dernières font travailler.
    Les solutions partent dans un document séparé, qui reste chez l'adulte.
    """
    if de > a:
        typer.secho(
            f"Le niveau de départ ({de}) dépasse celui d'arrivée ({a}).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)
    if seed is None:
        seed = secrets.randbits(32)

    try:
        puzzles = generate_ramp(de, a, nombre, seed)
    except GenerationError as error:
        typer.secho(f"Échec de génération : {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error

    destination = sortie or dossier / _default_path(
        "carnet", joueur, seed, puzzles, SUFFIX[format_]
    )
    cover = Cover(
        title=titre,
        subtitle=f"{nombre} grilles, du niveau {de} « {BY_NUMBER[de].name} »"
        f" au niveau {a} « {BY_NUMBER[a].name} »",
    )
    _write(puzzles, destination, format_, solutions=solutions, player=joueur, cover=cover)

    typer.secho(f"{len(puzzles)} grilles, niveaux {de} à {a} → {destination}", bold=True)
    counts = Counter(puzzle.rating.level for puzzle in puzzles)
    for level in sorted(counts):
        typer.echo(
            f"  niveau {level:>2} « {BY_NUMBER[level].name:<14} » {counts[level]:>3} grilles"
        )
    typer.echo(f"  seed du carnet : {seed}")
    _announce_solutions(solutions, destination)


@app.command()
def export(
    de: Annotated[
        int, typer.Option("--de", min=1, max=len(LEVELS), help="Premier niveau exporté.")
    ] = 1,
    a: Annotated[
        int, typer.Option("--a", min=1, max=len(LEVELS), help="Dernier niveau exporté.")
    ] = 10,
    par_niveau: Annotated[
        int, typer.Option("--par-niveau", "-c", min=1, help="Grilles par niveau.")
    ] = 20,
    sortie: Annotated[
        Path | None, typer.Option("--out", "-o", help="Fichier précis à écrire.")
    ] = None,
    dossier: Annotated[
        Path, typer.Option("--dossier", "-d", help="Dossier de sortie.")
    ] = OUTPUT_DIR,
    seed: Annotated[
        int | None, typer.Option("--seed", help="Rend la banque reproductible.")
    ] = None,
    lisible: Annotated[
        bool, typer.Option("--lisible", help="Indente le JSON, au prix de la taille.")
    ] = False,
) -> None:
    """Écrit une banque de grilles en JSON.

    De quoi alimenter un site statique : la génération et le classement restent
    ici, où ils sont testés et calibrés, et le site n'a plus qu'à piocher. Rien
    ne demande de rejouer un solveur côté navigateur.
    """
    if de > a:
        typer.secho(f"Le niveau {de} dépasse {a}.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    if seed is None:
        seed = secrets.randbits(32)

    wanted = list(range(de, a + 1))
    puzzles: list[Puzzle] = []
    try:
        for position, level in enumerate(wanted, start=1):
            typer.echo(f"  [{position}/{len(wanted)}] niveau {level}…", err=True, nl=False)
            batch = generate_many(level, par_niveau, seed + level)
            puzzles.extend(batch)
            typer.echo(
                f"\r  [{position}/{len(wanted)}] niveau {level} : {len(batch)} grilles", err=True
            )
    except GenerationError as error:
        typer.secho(f"Échec de génération : {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error

    bank: Bank = {
        "version": __version__,
        "generated": f"{date.today():%Y-%m-%d}",
        "seed": seed,
        "levels": [
            {"number": level.number, "name": level.name}
            for level in LEVELS
            if level.number in wanted
        ],
        "puzzles": [
            {
                "id": puzzle.identifier,
                "level": puzzle.rating.level,
                "givens": puzzle.rating.givens,
                "seed": puzzle.seed,
                "puzzle": puzzle.board.to_string(),
                "solution": puzzle.solution.to_string(),
            }
            for puzzle in puzzles
        ],
    }

    destination = sortie or dossier / _default_path("banque", None, seed, puzzles, ".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(bank, ensure_ascii=False, indent=2 if lisible else None),
        encoding="utf-8",
    )

    size = destination.stat().st_size
    typer.secho(
        f"{len(puzzles)} grilles, niveaux {de} à {a} → {destination}  ({size / 1024:.0f} Ko)",
        bold=True,
    )
    typer.echo(f"  seed de la banque : {seed}")


def _write(
    puzzles: Sequence[Puzzle],
    destination: Path,
    format_: Format,
    *,
    solutions: bool,
    player: str | None,
    cover: Cover | None = None,
) -> None:
    """Write the booklet, and its solutions alongside as a separate document."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    renderer = RENDERERS[format_]()
    renderer.render(puzzles, destination, cover=cover, player=player)
    if solutions:
        answers = Cover(title="Solutions", subtitle=cover.subtitle) if cover else None
        renderer.render_solutions(puzzles, _beside(destination, "solutions"), cover=answers)


def _announce_solutions(solutions: bool, destination: Path) -> None:
    if solutions:
        typer.secho(f"  solutions → {_beside(destination, 'solutions')}", fg=typer.colors.BLUE)


if __name__ == "__main__":
    app()
