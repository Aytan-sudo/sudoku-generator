/**
 * Le hasard doit être rejouable, et malgré tout du hasard.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { branch, mulberry32, shuffled, weighted } from "../js/rng.js";

test("la même graine donne la même suite", () => {
  const first = Array.from({ length: 20 }, mulberry32(7));
  const second = Array.from({ length: 20 }, mulberry32(7));
  assert.deepEqual(first, second);
});

test("deux graines donnent deux suites", () => {
  assert.notDeepEqual(
    Array.from({ length: 20 }, mulberry32(7)),
    Array.from({ length: 20 }, mulberry32(8)),
  );
});

test("les tirages tiennent dans [0, 1[", () => {
  const rng = mulberry32(1234);
  for (let index = 0; index < 5000; index += 1) {
    const value = rng();
    assert.ok(value >= 0 && value < 1, `${value}`);
  }
});

test("ils se répartissent sur l'intervalle", () => {
  // Pas un test de qualité du générateur : de quoi voir une suite constante ou
  // coincée dans une moitié, ce qui fausserait tous les tirages du site.
  const rng = mulberry32(99);
  const buckets = new Array(10).fill(0);
  for (let index = 0; index < 10000; index += 1) buckets[Math.floor(rng() * 10)] += 1;
  for (const count of buckets) assert.ok(count > 700 && count < 1300, buckets.join(" "));
});

test("une graine dérivée par niveau ne collisionne pas", () => {
  const seeds = new Set();
  for (let level = 1; level <= 10; level += 1) seeds.add(branch(4242, level));
  assert.equal(seeds.size, 10);
  // Et elle reste une fonction : deux appels, même réponse.
  assert.equal(branch(4242, 3), branch(4242, 3));
  assert.notEqual(branch(4242, 3), branch(4243, 3));
});

test("le mélange rend une permutation, sans toucher à l'original", () => {
  const items = Array.from({ length: 50 }, (_, index) => index);
  const mixed = shuffled(mulberry32(5), items);
  assert.equal(mixed.length, items.length);
  assert.deepEqual([...mixed].sort((a, b) => a - b), items);
  assert.deepEqual(items, Array.from({ length: 50 }, (_, index) => index));
  assert.notDeepEqual(mixed, items);
});

test("le mélange atteint toutes les positions", () => {
  // Une erreur classique de Fisher-Yates laisse le dernier élément en place.
  const last = new Set();
  for (let seed = 0; seed < 60; seed += 1) {
    last.add(shuffled(mulberry32(seed), [0, 1, 2, 3, 4])[4]);
  }
  assert.equal(last.size, 5);
});

test("le tirage pondéré suit les poids", () => {
  const rng = mulberry32(11);
  const items = [
    { name: "gros", count: 90 },
    { name: "petit", count: 10 },
  ];
  const counts = { gros: 0, petit: 0 };
  for (let index = 0; index < 4000; index += 1) {
    counts[weighted(rng, items, (item) => item.count).name] += 1;
  }
  assert.ok(counts.gros > 3400 && counts.gros < 3800, JSON.stringify(counts));
  assert.ok(counts.petit > 200, JSON.stringify(counts));
});

test("un poids nul n'est jamais tiré", () => {
  const rng = mulberry32(3);
  const items = [
    { name: "vide", count: 0 },
    { name: "plein", count: 5 },
  ];
  for (let index = 0; index < 500; index += 1) {
    assert.equal(weighted(rng, items, (item) => item.count).name, "plein");
  }
});
