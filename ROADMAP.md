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

## Étape 4 — Générateur

- [ ] Grille complète valide (backtracking, ordre des candidats mélangé)
- [ ] Creusage avec vérification d'unicité à chaque retrait
- [ ] Ciblage : refus des retraits qui franchissent le plafond de technique visé
- [ ] Boucle « creuser, classer, recommencer » jusqu'à obtenir le niveau visé
- [ ] Garde-fou sur le nombre d'essais, avec erreur claire si la cible est inatteignable
- [ ] Reproductibilité par seed (`random.Random` explicite, jamais le `random` global)
- [ ] Tests : niveau produit conforme à la cible, déterminisme de la seed

## Étape 5 — Rendu PDF ◄── **première impression utilisable**

- [ ] `render/base.py` — interface `Renderer`
- [ ] `render/pdf.py` — ReportLab, A4, grille 162 mm centrée (cellule 18 mm)
- [ ] Filets : cellules 0,4 pt gris 40 % / blocs 1,6 pt / cadre 2 pt
- [ ] Chiffres centrés **optiquement** (via ascender/descender, pas `height / 2`)
- [ ] En-tête : « Sudoku · Niveau N sur 10 — Nom » + jauge à 10 pastilles
- [ ] Ligne prénom / temps
- [ ] Pied de page : identifiant de grille + seed + date
- [ ] `render/text.py` — rendu terminal pour le débogage

## Étape 6 — CLI

- [ ] `sudoku generate --niveau --nombre --seed --solutions -o`
- [ ] Pages de solutions regroupées en fin de document
- [ ] Messages d'erreur clairs (niveau hors bornes, cible inatteignable…)

## Étape 7 — Techniques avancées (niveaux 7 à 10)

- [ ] Candidats verrouillés — *pointing* et *claiming* (niveau 7)
- [ ] Paires et triplets nus (niveau 8)
- [ ] Paires et triplets cachés (niveau 8)
- [ ] X-Wing (niveau 9)
- [ ] XY-Wing (niveau 9)
- [ ] Fixtures de test générées par le générateur lui-même, une par technique
- [ ] Recalibrage des seuils du classificateur sur un échantillon

## Étape 8 — Carnet

- [ ] Fonction de rampe : répartir N grilles entre deux niveaux
- [ ] `sudoku carnet --de --a --nombre -o`
- [ ] Page de garde
- [ ] Section solutions en fin de carnet

## Étape 9 — Finitions

- [ ] README complété avec exemples et PDF d'illustration
- [ ] Vérification à l'impression réelle (lisibilité des chiffres, contraste des filets)
- [ ] Passe de performance si nécessaire

---

## Hors périmètre (décidé)

- **Symétrie** du motif des cases vides — purement esthétique, et nuit au contrôle fin du nombre
  d'indices.
- **Swordfish, Jellyfish** — généralisations du X-Wing au gain de discrimination négligeable ici.
- **Forcing chains / nice loops** — inutiles : le niveau 10 se définit par l'épuisement du
  catalogue, pas par une technique de plus.
- **Interface graphique, résolution assistée à l'écran** — le livrable est un PDF à imprimer.
