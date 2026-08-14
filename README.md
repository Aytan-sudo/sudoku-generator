# sudoku-generator

Générateur de sudokus avec **classificateur de difficulté sur 10 niveaux** et sortie **PDF A4**
prête à imprimer.

Le projet vise d'abord un usage familial : produire des grilles calibrées pour une enfant de 11 ans
qui débute, avec une échelle assez fine pour accompagner sa progression sur la durée.

## Le principe

La difficulté d'un sudoku **ne dépend pas du nombre de cases vides**. Une grille à 24 indices peut
être triviale, une grille à 30 indices peut être redoutable. Ce qui compte, ce sont les **techniques
de résolution nécessaires** pour la terminer.

Le projet s'appuie donc sur deux solveurs distincts :

| Solveur | Rôle |
| --- | --- |
| **Machine** — backtracking à masques de bits | Vérifier qu'une grille admet **exactement une** solution |
| **Humain** — logique déductive à catalogue | Résoudre *comme un joueur*, en journalisant les techniques employées |

C'est le second qui attribue la note.

## L'échelle de difficulté

Sous le niveau 7, ce sont le **nombre d'indices** et le **goulot d'étranglement** qui classent.
À partir du niveau 7, c'est le **plafond de technique** qui domine.

Le goulot d'étranglement est le nombre minimal de coups jouables simultanément rencontré au cours
de la résolution. À technique identique, une grille qui n'offre parfois qu'un seul coup possible est
bien plus difficile à percer qu'une grille qui en offre huit.

| Niv. | Nom | Plafond de technique | Indices | Goulot |
| --- | --- | --- | --- | --- |
| 1 | Découverte | Dernière case | 55-62 | ≥ 8 coups |
| 2 | Premiers pas | + Single caché (bloc) | 48-54 | ≥ 6 |
| 3 | Facile | idem | 42-47 | ≥ 4 |
| 4 | Facile + | + Single caché (ligne/colonne) | 38-43 | ≥ 3 |
| 5 | Moyen | + Single nu | 34-38 | ≥ 2 |
| 6 | Moyen + | idem | 31-35 | ≥ 1 |
| 7 | Confirmé | + Candidats verrouillés | 29-33 | — |
| 8 | Difficile | + Paires / triplets (nus et cachés) | 27-31 | — |
| 9 | Expert | + X-Wing, XY-Wing | 24-29 | — |
| 10 | Diabolique | Hors catalogue | 22-27 | — |

Le niveau 10 ne se détecte pas par une technique supplémentaire : c'est le cas où **le catalogue est
épuisé** sans que la grille soit résolue. Les *forcing chains* ne sont donc jamais implémentées.

## Décisions de conception

- **Pas de symétrie** dans le motif des cases vides. C'est une pure convention esthétique de
  magazine, et creuser par paires empêcherait de contrôler le nombre d'indices au chiffre près —
  or c'est le levier principal du réglage des niveaux 1 à 6.
- **Génération ciblée, pas subie.** On creuse vers la fourchette d'indices visée en refusant tout
  retrait qui ferait franchir le plafond de technique, puis on vérifie le goulot.
- **Reproductibilité.** Un `random.Random(seed)` passé explicitement partout, jamais le `random`
  global. Même seed, même PDF. La seed est imprimée en pied de page.
- **Rendu découplé.** Une interface `Renderer` isole le format de sortie ; ReportLab n'en est qu'une
  implémentation.

## Installation

```bash
uv sync
```

## Usage

> Le code métier n'est pas encore écrit — voir [ROADMAP.md](ROADMAP.md) pour l'avancement.

Interface visée :

```bash
# Une grille de niveau 4
uv run sudoku generate --niveau 4 -o grille.pdf

# Cinq grilles de niveau 6, avec les solutions, reproductibles
uv run sudoku generate --niveau 6 --nombre 5 --seed 42 --solutions -o grilles.pdf

# Un carnet de 20 grilles en rampe progressive du niveau 3 au niveau 6
uv run sudoku carnet --de 3 --a 6 --nombre 20 -o carnet.pdf
```

## Développement

```bash
uv run pytest          # tests
uv run ruff check .    # lint
uv run ruff format .   # formatage
uv run mypy            # typage
```

## Licence

MIT
