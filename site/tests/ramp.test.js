/**
 * La rampe doit rendre exactement ce que le Python rend.
 *
 * Les vecteurs viennent de `tools/fixtures.py`, qui les tire de
 * `generator.ramp()`. `tests/test_site.py` vérifie de son côté que le fichier
 * est à jour : à eux deux, ils empêchent l'une des deux implémentations de
 * bouger seule.
 */

import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";

import { ramp } from "../js/draw.js";

const cases = JSON.parse(
  readFileSync(new URL("./fixtures/ramp.json", import.meta.url), "utf8"),
);

test("la rampe rend les mêmes niveaux que le générateur Python", () => {
  assert.ok(cases.length > 0, "aucun vecteur : lancer tools/fixtures.py");
  for (const { start, end, count, levels } of cases) {
    assert.deepEqual(
      ramp(start, end, count),
      levels,
      `ramp(${start}, ${end}, ${count})`,
    );
  }
});

test("elle donne toujours le nombre de grilles demandé", () => {
  for (const { start, end, count } of cases) {
    assert.equal(ramp(start, end, count).length, count);
  }
});

test("elle monte, sans jamais redescendre", () => {
  for (const { start, end, count } of cases) {
    const levels = ramp(start, end, count);
    for (let index = 1; index < levels.length; index += 1) {
      assert.ok(levels[index] >= levels[index - 1], `${levels}`);
    }
    assert.ok(levels[0] >= start);
    assert.ok(levels[levels.length - 1] <= end);
  }
});

test("le reste va vers le bas, pas vers le haut", () => {
  // Un carnet est un meilleur endroit pour commencer doucement que pour finir
  // brutalement : sur 7 grilles et 3 niveaux, c'est 3-2-2 et non 2-2-3.
  const levels = ramp(1, 3, 7);
  assert.deepEqual(levels, [1, 1, 1, 2, 2, 3, 3]);
});

test("elle refuse un intervalle à l'envers ou un compte nul", () => {
  assert.throws(() => ramp(6, 3, 10), /dépasse/);
  assert.throws(() => ramp(1, 10, 0), /au moins 1/);
});
