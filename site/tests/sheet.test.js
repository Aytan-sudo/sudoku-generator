/**
 * La feuille : le bon nombre de pages, aux bonnes coordonnées.
 *
 * Ce que ces tests ne peuvent pas voir — que la feuille ressemble à celle des
 * carnets déjà imprimés — se vérifie avec `tools/compare_render.py`, qui rend
 * les deux et compare les pixels.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import * as L from "../js/layout.js";
import { headline, formatDate, render, renderSolutions } from "../js/sheet.js";

const PUZZLE = "53..7....6..195...98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79";
const SOLUTION = "534678912672195348198342567859761423426853791713924856961537284287419635345286179";

function puzzle(number, level = 3) {
  return {
    id: `abcdef${number}`,
    level,
    levelName: "Facile",
    givens: 30,
    seed: 1234,
    puzzle: `${PUZZLE}..`.slice(0, 81),
    solution: SOLUTION,
  };
}

function text(bytes) {
  return String.fromCharCode(...bytes);
}

function pages(bytes) {
  return Number(text(bytes).match(/\/Count (\d+)/)[1]);
}

const TODAY = new Date(2026, 7, 16);

test("une grille tient sur une page", () => {
  assert.equal(pages(render([puzzle(1)], { today: TODAY })), 1);
});

test("la page de garde en ajoute une, et une seule", () => {
  const cover = { title: "Carnet de sudokus", subtitle: "20 grilles" };
  assert.equal(pages(render([puzzle(1), puzzle(2)], { cover, today: TODAY })), 3);
});

test("les solutions vont six par page, sans feuille blanche en tête", () => {
  const many = Array.from({ length: 13 }, (_, index) => puzzle(index));
  const bytes = renderSolutions(many);
  assert.equal(pages(bytes), 3);
  assert.ok(text(bytes).includes("(Solutions)"));
});

test("un document vide est refusé plutôt que rendu blanc", () => {
  assert.throws(() => render([], {}), /aucune grille/);
  assert.throws(() => renderSolutions([]), /aucune grille/);
});

test("le titre de la feuille est celui du générateur", () => {
  assert.equal(headline(3, "Facile"), "Niveau 3 sur 10 — Facile");
  const document = text(render([puzzle(1)], { today: TODAY }));
  // « — » est hors Latin-1 : il doit sortir en WinAnsi, échappé en octal.
  assert.ok(document.includes("(Sudoku  \\267  Niveau 3 sur 10 \\227 Facile)"));
});

test("la grille est un carré de 180 mm, centré, à sa hauteur de page", () => {
  const document = text(render([puzzle(1)], { today: TODAY }));
  const size = (180 * L.MM).toFixed(3).replace(/0+$/, "");
  const left = (15 * L.MM).toFixed(3).replace(/0+$/, "");
  const bottom = (62 * L.MM).toFixed(3).replace(/0+$/, "");
  assert.ok(
    document.includes(`${left} ${bottom} ${size} ${size} re`),
    `cadre introuvable : ${left} ${bottom} ${size}`,
  );
});

test("le pied porte de quoi retrouver la grille", () => {
  const document = text(render([puzzle(7)], { today: TODAY }));
  assert.ok(document.includes("n\\260 abcdef7"), "l'identifiant manque");
  assert.ok(document.includes("30 indices"), "le nombre d'indices manque");
  assert.ok(document.includes("seed 1234"), "la graine manque");
  assert.ok(document.includes("16/08/2026"), "la date manque");
});

test("le prénom connu est imprimé, l'inconnu est réglé", () => {
  const named = text(render([puzzle(1)], { player: "Louane", today: TODAY }));
  assert.ok(named.includes("(Louane)"));

  const anonymous = text(render([puzzle(1)], { today: TODAY }));
  assert.ok(!anonymous.includes("(Louane)"));
  // Sans prénom, la ligne à remplir est tracée : un trait de plus sur la page.
  assert.ok(anonymous.split(" l S").length > named.split(" l S").length);
});

test("la date s'écrit à la française", () => {
  assert.equal(formatDate(new Date(2026, 0, 5)), "05/01/2026");
  assert.equal(formatDate(new Date(2026, 11, 31)), "31/12/2026");
});

test("la jauge dessine dix points, remplis jusqu'au niveau", () => {
  const document = text(render([puzzle(1, 4)], { today: TODAY }));
  // Un cercle vaut quatre courbes ; dix cercles, quarante.
  assert.equal(document.match(/ c /g).length, 40);
  // Remplis jusqu'à 4 : quatre points d'encre, six blancs.
  assert.equal(document.match(/0\.15 g/g).length, 4);
  assert.equal(document.match(/\n1 g/g).length, 6);
});
