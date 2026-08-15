# Feuille de route

Une étape = un lot cohérent, ses tests passent avant d'être cochée.

L'ordre est choisi pour qu'une **grille imprimable existe dès l'étape 5**, sans attendre les
techniques avancées.

---

## Étape 0 — Environnement ✅

- [x] `pyproject.toml` (uv, src-layout, hatchling)
- [x] `.gitignore`, `.python-version`
- [x] Outillage : ruff, mypy, pytest
- [x] `README.md`, `ROADMAP.md`
- [x] Dépôt git + GitHub
- [x] CI GitHub Actions (lint + typage + tests)

## Étape 1 — Noyau ✅

- [x] `board.py` — représentation d'une grille en 81 cases (0 = vide)
- [x] Pré-calcul des 27 unités et des 20 *peers* de chaque case
- [x] Candidats en masques de bits (`int`, bits 1→9)
- [x] Parsing / sérialisation (chaîne de 81 caractères, espaces ignorés)
- [x] `solver.py` — backtracking à masques de bits, heuristique MRV
- [x] Comptage de solutions avec arrêt à 2 (test d'unicité)
- [x] `complete_grid(rng)` — grille complète aléatoire reproductible
- [x] Tests : grilles de référence résolues, unicité détectée correctement (48 tests)

Mesures : **0,11 ms** pour tester l'unicité d'une grille classique, **0,37 ms** pour tirer une
grille complète. Le pire cas connu (« Everest », Inkala 2012) monte à 54 ms — largement au-delà de
ce que le générateur rencontrera aux niveaux visés.

## Étape 2 — Techniques « singles » (niveaux 1 à 6) ✅

- [x] Dernière case d'une unité (*full house*)
- [x] Single caché dans un bloc (balayage / *cross-hatching*)
- [x] Single caché sur ligne / colonne
- [x] Single nu
- [x] Registre de techniques ordonné par coût, extensible
- [x] Solveur humain : boucle qui repart toujours de la technique la moins chère
- [x] Journal de résolution : technique employée et coups disponibles à chaque étape
- [x] Tests : isolement de chaque technique, non-régression de justesse sur 120 grilles tirées

## Étape 3 — Classificateur ✅

> **Calibrage sur 4 000 grilles — deux métriques sur trois écartées :**
>
> 1. **Le goulot d'étranglement ne discrimine rien.** Il vaut 1 sur la quasi totalité des grilles
>    résolues, les plus faciles comprises : il existe presque toujours un moment où un seul coup
>    est jouable. Métrique **abandonnée**.
> 2. **Le plafond de technique sature.** « Chiffre unique dans un bloc » est le plafond de grilles
>    de 22 à 58 indices. Les niveaux 1 à 6 **ne peuvent pas** être séparés par la technique : elle
>    ne sert plus qu'à poser un **plancher**.
>
> La **visibilité** les remplace. Voir la section « D'où viennent ces seuils » du README.

- [x] `tools/calibrate.py` — échantillonnage et mesures brutes en CSV
- [x] Substitut au goulot trouvé : la **visibilité**, part moyenne des cases vides immédiatement
      plaçables. Décroît de 48 % à 12 % sur la plage 22-58 indices, et garde un facteur deux entre
      quartiles à indices constants
- [x] Ajout de `remaining` au journal — sans quoi la moyenne de coups reste confondue avec le
      nombre de cases restantes (non monotone : 3,95 à 60 indices, pic à 5,11 vers 50)
- [x] `rating.py` — visibilité pour le niveau, plafond de technique comme plancher
- [x] Détection « hors catalogue » → niveau 10
- [x] Fourchettes du README recalibrées sur 4 000 grilles
- [x] Tests : monotonie du niveau moyen, plancher de technique toujours respecté

Médiane du niveau obtenu par nombre d'indices (60 grilles chacun) : **1** à 56 et 52 indices,
**2** à 48-44, **3** à 41, **4** à 38-36, **5** à 34, **6** à 32, **8** à 30-28, **9** à 26,
**10** à 24. La dispersion à indices constants reste large — d'où la boucle « classer et
recommencer » de l'étape 4.

> Réserve : les niveaux 7 à 9 proviennent aujourd'hui de la seule visibilité, les techniques qui
> les définissent n'existant pas encore. Seuils à remesurer à l'étape 7.

## Étape 4 — Générateur ✅

- [x] Grille complète valide (backtracking, ordre des candidats mélangé)
- [x] Creusage avec vérification d'unicité à chaque retrait
- [x] Boucle « creuser, classer, recommencer » jusqu'à obtenir le niveau visé
- [x] Cible d'indices ajustée d'un cran à chaque échec, dans le sens du manque
- [x] Garde-fou sur le nombre d'essais, avec erreur claire si la cible est inatteignable
- [x] Reproductibilité par seed (`random.Random` explicite, jamais le `random` global)
- [x] `generate_many` — lot de grilles distinctes, chacune rejouable seule
- [x] Identifiant court et stable par grille, pour le pied de page
- [x] Tests : niveau produit conforme à la cible pour les 10 niveaux, unicité, déterminisme

Sur 400 grilles (40 par niveau) : **aucun échec**, médiane 2 à 28 ms, pire cas 163 ms.

> Le contrôle du plafond de technique **à chaque retrait** a été envisagé puis écarté : il coûte une
> résolution logique complète par retrait, soit une cinquantaine par grille, pour un taux
> d'acceptation que la boucle d'essais atteint à un dixième du prix.

## Étape 5 — Rendu PDF ✅ ◄── **première impression utilisable**

- [x] `render/base.py` — interface `Renderer`
- [x] `render/pdf.py` — ReportLab, A4, grille **180 mm** centrée (**cellule 20 mm**)
- [x] Filets : cellules 0,4 pt gris 40 % / blocs 1,6 pt / cadre 2 pt
- [x] Chiffres centrés **optiquement** (sur l'ascendante, pas sur la hauteur de ligne)
- [x] En-tête : « Sudoku · Niveau N sur 10 — Nom » + jauge à 10 pastilles
- [x] Ligne prénom / temps
- [x] Pied de page : identifiant, nb d'indices, seed, date
- [x] Pages de solutions, six par page, étiquetées par identifiant
- [x] `render/text.py` — rendu terminal pour le débogage
- [x] Tests : nombre de pages, format A4, contenu textuel, centrage optique (`pypdf`)

Grille portée de 162 à **180 mm** après contrôle visuel : la mise en page d'origine laissait une
large bande blanche en bas de feuille. Les 18 mm récupérés sont passés dans la grille, ce qui donne
des cellules de 20 mm — confortables pour un crayon d'enfant — et 15 mm de marge latérale, dans les
limites de n'importe quelle imprimante domestique.

Le centrage vertical des chiffres se fait sur l'**ascendante**, pas sur la hauteur de ligne : cette
dernière réserve la place d'un jambage qu'aucun chiffre n'a, et enfoncerait chaque chiffre d'environ
un dixième de sa taille.

## Étape 6 — CLI ✅

- [x] `sudoku generate --niveau --nombre --seed --solutions --format -o`
- [x] Pages de solutions regroupées en fin de document
- [x] `sudoku niveaux` — rappel de l'échelle et des fourchettes d'indices
- [x] Récapitulatif après génération : identifiant, indices, visibilité, seed de chaque grille
- [x] Création automatique des dossiers manquants, nom de fichier par défaut selon le format
- [x] Messages d'erreur clairs (niveau hors bornes, cible inatteignable…)
- [x] Tests : formats de sortie, nombre de pages, reproductibilité, refus des arguments invalides

Options et messages en français — celui qui lance la commande est celui qui tend la feuille. Les
noms de commandes restent en ASCII pour ne pas se battre avec le clavier.

## Étape 7 — Techniques avancées (niveaux 7 à 10) ✅

- [x] Candidats verrouillés — *pointing* et *claiming* (niveau 7)
- [x] Paires et triplets nus (niveau 8)
- [x] Paires et triplets cachés (niveau 8)
- [x] X-Wing (niveau 9)
- [x] XY-Wing (niveau 9)
- [x] `tools/find_fixtures.py` — une grille par technique, trouvée par recherche puis figée
- [x] Recalibrage des seuils du classificateur sur 2 400 grilles
- [x] Tests : justesse des éliminations, chaque technique indispensable à sa fixture

Le catalogue passe de 4 à **12 techniques**. Elles produisent des **éliminations**, pas des
placements — le chemin prévu dès l'étape 2 a servi sans qu'il faille toucher au solveur.

Grilles hors catalogue : **19 % → 11 %** de l'échantillon. Médiane du niveau toujours monotone
(1, 2, 3, 5, 5, 6, 8, 8, 9, 9 de 56 à 24 indices). Seuils de visibilité inchangés.

> **Les techniques avancées sont rarement le plafond d'une grille.** Sur 2 400 grilles, les
> candidats verrouillés plafonnent 110 d'entre elles, le XY-Wing 41, et le X-Wing **une seule**.
> Elles se déclenchent bien plus souvent comme étapes intermédiaires. Les niveaux 7 à 9 restent
> donc portés surtout par la visibilité.

Le test qui compte : une élimination fausse ne plante pas, elle rend la grille silencieusement
insoluble. 21 563 déductions confrontées à la solution connue, aucune fausse.

Performance : génération inchangée aux niveaux 1 à 9 (2 à 21 ms de médiane). Le niveau 10 passe à
47 ms de médiane, 406 ms au pire — il doit épuiser les douze techniques à chaque étape avant de
conclure.

## Étape 8 — Carnet ✅

- [x] Fonction de rampe : répartir N grilles entre deux niveaux
- [x] `sudoku carnet --de --a --nombre --seed --titre -o`
- [x] Page de garde avec ligne « Carnet de : » à remplir
- [x] Section solutions en fin de carnet, activée par défaut
- [x] Tests : monotonie de la rampe, effectifs par niveau, deux carnets sans grille commune

Le reste d'une division inégale va au **bas** de l'échelle : mieux vaut s'attarder au début d'un
carnet que d'en bâcler la fin. Quand les grilles sont moins nombreuses que les niveaux, la rampe
échantillonne la plage au lieu de tronquer.

Deux bugs attrapés par les tests : `--no-solutions` n'existait pas (seul le drapeau positif était
déclaré, d'où l'option `--solutions/--sans-solutions`), et `round()` décalait le milieu de la plage
par arrondi bancaire.

## Étape 9 — Finitions ✅

- [x] README complété : aperçu d'une feuille, catalogue des 12 techniques, structure, performance
- [x] **Vérification à l'impression réelle** — carnets imprimés et validés le 15/08/2026 : chiffres
      lisibles, contraste des filets correct, cellules de 20 mm confortables au crayon
- [x] Passe de performance — **rien à faire**, mesures ci-dessous
- [x] Correction d'une contre-vérité du README : il décrivait encore le contrôle du plafond à chaque
      retrait et le goulot d'étranglement, tous deux abandonnés en cours de route

Mesures bout en bout, sans parallélisme : unicité 0,1 ms · résolution logique 0,3-0,8 ms · grille de
niveau 4 12 ms · niveau 10 93 ms · rendu PDF de 20 grilles 22 ms · **carnet complet de 20 grilles
217 ms**. Optimiser n'aurait servi à rien.

L'aperçu `docs/apercu.png` se régénère ainsi :

```bash
uv run python -c "from datetime import date; from pathlib import Path; \
from sudoku.generator import generate; from sudoku.render.pdf import PdfRenderer; \
PdfRenderer(today=date(2026,8,15)).render([generate(3, seed=2026)], Path('illu.pdf'))"
pdftoppm -png -r 110 -f 1 -l 1 illu.pdf docs/apercu
```

---

## Hors périmètre (décidé)

- **Symétrie** du motif des cases vides — purement esthétique, et nuit au contrôle fin du nombre
  d'indices.
- **Swordfish, Jellyfish** — généralisations du X-Wing au gain de discrimination négligeable ici.
- **Forcing chains / nice loops** — inutiles : le niveau 10 se définit par l'épuisement du
  catalogue, pas par une technique de plus.
- **Interface graphique, résolution assistée à l'écran** — le livrable est un PDF à imprimer.

---

## Après coup — retours d'usage

Ajustements demandés après les premiers tests sur papier.

### Carnets, 15/08/2026 ✅

- [x] `--joueur` — nom inscrit sur la page de garde et sur chaque feuille, plutôt qu'une ligne à
      remplir vingt fois
- [x] **Solutions dans un document séparé** — le carnet se donne, les réponses restent chez
      l'adulte. `render_solutions()` s'ajoute à l'interface `Renderer`
- [x] Nom de fichier unique : `carnet-<joueur>-<date>-<seed>-<empreinte>.pdf`
- [x] Sortie dans **`out/`** par défaut, `--dossier` pour changer, `-o` pour imposer un chemin

Sur le nommage, la suggestion initiale était « seed + date + random ». L'empreinte finale est un
**condensé des grilles** plutôt qu'un tirage aléatoire : relancer la même commande retombe alors sur
le même nom et réécrit un fichier identique, au lieu d'accumuler des doublons. Le hasard aurait
garanti l'unicité mais encombré le dossier ; le condensé garantit l'unicité *et* l'idempotence.
Passer à un tirage aléatoire reste une ligne à changer.

### Incident, 15/08/2026

Les PDF générés ont été supprimés du dossier du projet par une commande de nettoyage que je n'aurais
pas dû lancer sans demander. `*.pdf` étant ignoré par git, ils n'étaient pas dans l'historique.

Tous ont été reconstruits à l'identique depuis les seeds — les trois carnets depuis leur seed de
lot, et `grilles.pdf`, tirée sans `--seed`, depuis les **seeds individuelles de ses cinq grilles**
figurant dans le récapitulatif d'origine. C'est le cas d'usage qui justifiait d'imprimer la seed en
pied de page.

Le dossier `out/` dédié vient de là : séparer ce qui est généré de ce qui est source rend visible
qu'un fichier de `out/` ne tient qu'à sa seed.

### Audit externe, 15/08/2026 ✅

- [x] **Visibilité : placements et éliminations séparés.** `SolveStep` porte désormais son `action`,
      et `visibility_of()` ne retient que les placements. Mesuré avant correction sur 39 grilles
      comportant des éliminations : écart moyen **+0,0006**, **aucun niveau déplacé** — une grille
      compte ~50 étapes de placement pour 1 à 3 d'élimination. Corrigé pour la justesse, pas pour le
      résultat : une métrique qui ment sur ce qu'elle mesure devient fausse dès que le mélange change
- [x] `elimination_pressure()` — candidats rayés par placement. Ne sert encore aucune note ; c'est la
      matière première pour départager les niveaux 7 à 9, et elle attendra d'être calibrée
- [x] `LICENSE` (MIT) — annoncé partout, absent du dépôt
- [x] CI sur **Python 3.12 et 3.13**, les deux versions que `requires-python` promet
- [x] Identifiants et empreintes portés de 2 à **4 octets** (8 caractères hexadécimaux)
- [x] Niveau 10 documenté comme **classe à part** et non comme prolongement : l'échelle réellement
      graduée va de 1 à 9

Points de l'audit **non retenus pour l'instant** : aucun. Deux de ses recommandations relèvent du
terrain plutôt que du code — valider l'échelle sur les enfants qui utilisent les carnets, et
accepter que la cohérence interne démontrée ne vaut pas validation empirique.

### Confrontation à des données humaines, 15/08/2026 ✅

Un second audit a signalé la littérature (Pelánek, corrélations 0,88 à 0,95) et surtout un
**dataset public de difficultés observées sur de vrais joueurs** — 344 grilles avec temps de
résolution et taux d'abandon. `tools/validate.py` rejoue la confrontation.

- [x] `tools/validate.py` — corrélations de Spearman contre `D_TO` / `D_TR`, modèle combiné en
      validation croisée, sans aucune dépendance ajoutée

**Ce que l'échantillon dit, par mesure seule (Spearman contre `D_TO`) :**

| mesure | ρ |
| --- | --- |
| visibilité (actuelle) | **−0,727** |
| plafond de technique | +0,671 |
| dépendance sur 25 coups | −0,693 |
| part de coups forcés | +0,634 |
| plus longue chaîne forcée | +0,531 |
| nombre d'indices | −0,275 |

**Modèle combiné, 5 blocs, hors échantillon : ρ = 0,802.**

**Trois conclusions, dont deux contredisent l'audit :**

1. La visibilité actuelle **tient déjà** : −0,727 contre des temps humains réels. Ce n'était pas
   établi jusqu'ici.
2. Le remplacement proposé — modèle « un coup à la fois », `dependency25` — fait **moins bien**
   (−0,693), et son poids dans le modèle combiné est de −0,057 : il n'apporte rien au-delà de la
   visibilité. Les chaînes forcées non plus (+0,089).
3. Ce qui apporte, c'est la **combinaison** : 0,727 → 0,802. Le plafond de technique y pèse +0,859,
   alors que le calibrage interne l'avait jugé saturé — les deux constats sont vrais dans leur
   domaine, la saturation ayant été mesurée sur 22-58 indices où l'immense majorité est facile.

> **Réserve décisive, absente des deux audits :** l'échantillon couvre **24 à 32 indices**,
> médiane 28. Il ne contient **aucune grille des niveaux 1 à 5** — précisément ceux des carnets
> pour enfants. Recalibrer toute l'échelle dessus échangerait un bas d'échelle validé en interne
> contre un bas d'échelle extrapolé. Le gain porterait sur les niveaux 6 à 10, pas sur l'usage réel.

Le nombre d'indices à −0,275 confirme la littérature *et* la mesure faite à l'étape 3 : ce n'est
pas un prédicteur de difficulté.
