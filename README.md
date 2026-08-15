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

Le niveau se lit sur la **visibilité** : la part moyenne des cases encore vides qui étaient
immédiatement plaçables à chaque étape. Une grille qui offre à tout instant la moitié de son
reliquat se remplit toute seule ; une grille qui n'en montre qu'un dixième se chasse.

Le **plafond de technique** ne sert qu'à *relever* le niveau : une grille qui force une technique
exigeante ne peut pas être classée facile, même si elle paraît aérée par ailleurs.

| Niv. | Nom | Visibilité | Plancher imposé par la technique | Indices typiques |
| --- | --- | --- | --- | --- |
| 1 | Découverte | ≥ 42 % | — | 50-58 |
| 2 | Premiers pas | ≥ 36 % | — | 44-50 |
| 3 | Facile | ≥ 30 % | — | 40-45 |
| 4 | Facile + | ≥ 25 % | — | 36-41 |
| 5 | Moyen | ≥ 21 % | Chiffre unique ligne/colonne | 33-37 |
| 6 | Moyen + | ≥ 18 % | Case à candidat unique | 31-34 |
| 7 | Confirmé | ≥ 16 % | Candidats verrouillés | 29-32 |
| 8 | Difficile | ≥ 14 % | Paires / triplets, nus et cachés | 27-30 |
| 9 | Expert | < 14 % | X-Wing, XY-Wing | 25-28 |
| 10 | Diabolique | — | Hors catalogue | 22-27 |

Le niveau 10 ne se détecte pas par une technique supplémentaire : c'est le cas où **le catalogue est
épuisé** sans que la grille soit résolue. Les *forcing chains* ne sont donc jamais implémentées.

Les fourchettes d'indices sont indicatives, pas prescriptives : à nombre d'indices constant, la
visibilité varie du simple au double d'une grille à l'autre. Le générateur creuse vers une
fourchette, puis **classe et recommence** si le niveau obtenu n'est pas celui visé.

### D'où viennent ces seuils

Ils sont mesurés, pas devinés. `tools/calibrate.py` creuse un large échantillon de grilles sur toute
la plage 22-58 indices et relève ce qui varie réellement avec la difficulté. Sur 4 000 grilles, deux
des trois métriques prévues à l'origine n'ont pas survécu :

- Le **goulot d'étranglement** — le minimum de coups jouables simultanément — vaut 1 sur la quasi
  totalité des grilles, y compris les plus faciles : il existe presque toujours un moment où un seul
  coup est sur la table. Métrique abandonnée.
- Le **plafond de technique** sature. « Chiffre unique dans un bloc » est le plafond de grilles
  allant de 22 à 58 indices : il ne peut donc pas séparer le bas de l'échelle. Conservé comme
  plancher uniquement.

La visibilité, elle, décroît proprement de 48 % à 54 indices jusqu'à 12 % à 23 indices, et conserve
un écart d'un facteur deux entre quartiles **à nombre d'indices constant** — c'est ce qui distingue
deux grilles semblables sur le papier et très différentes à résoudre.

Mesures refaites une fois les techniques avancées en place. Elles récupèrent une bonne part de ce
qui était insoluble — les grilles hors catalogue passent de 19 % à 11 % de l'échantillon — et
l'échelle reste monotone, si bien que les seuils de visibilité n'ont pas bougé.

Un constat mérite d'être noté : les techniques avancées sont rarement le **plafond** d'une grille.
Sur 2 400 grilles, les candidats verrouillés plafonnent 110 d'entre elles, le XY-Wing 41, et le
X-Wing exactement une. Elles se déclenchent bien plus souvent que ça comme étapes intermédiaires,
mais rarement comme la chose la plus dure qu'une grille exige. Les niveaux 7 à 9 restent donc
portés surtout par la visibilité, le plancher de technique n'intervenant que pour la minorité de
grilles qui tiennent vraiment à un wing ou à une paire verrouillée.

Reproduire les mesures :

```bash
uv run python tools/calibrate.py --per-floor 200 --out sample.csv
```

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

```bash
# Une grille de niveau 4
uv run sudoku generate --niveau 4 -o grille.pdf

# Cinq grilles de niveau 6, avec les solutions, reproductibles
uv run sudoku generate --niveau 6 --nombre 5 --seed 42 --solutions -o grilles.pdf

# Les grilles en texte, pour jeter un œil sans ouvrir de visionneuse
uv run sudoku generate --niveau 3 --format texte -o grilles.txt

# Rappel de l'échelle
uv run sudoku niveaux
```

La commande récapitule ce qu'elle a produit :

```
3 grilles de niveau 4 « Facile + » → grilles.pdf
  n° 3cd0   38 indices   visibilité 28%   seed 2746317213
  n° 9919   38 indices   visibilité 27%   seed 1181241943
  n° f391   38 indices   visibilité 27%   seed 958682846
```

`--seed` rejoue un lot entier à l'identique. Chaque grille porte en plus **sa propre seed** en pied
de page : elle peut être régénérée seule, indépendamment du lot dont elle est issue.

### Carnets

Un carnet monte en difficulté de page en page : les premières grilles mettent en confiance, les
dernières font travailler.

```bash
uv run sudoku carnet --de 3 --a 6 --nombre 20 --seed 111 -o carnet.pdf
```

Il s'ouvre sur une page de garde avec une ligne « Carnet de : » à remplir, et se termine par les
solutions. Deux carnets tirés avec des seeds différentes n'ont **aucune grille en commun** — de quoi
en donner un à chaque enfant sans qu'ils tombent sur les mêmes.

## Développement

```bash
uv run pytest          # tests
uv run ruff check .    # lint
uv run ruff format .   # formatage
uv run mypy            # typage
```

## Licence

MIT
