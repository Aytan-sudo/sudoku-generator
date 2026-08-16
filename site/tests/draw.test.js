/**
 * Le tirage : rejouable, sans doublon, et respectueux de ce qui est déjà sorti.
 *
 * La banque est simulée — ces tests portent sur le choix des grilles, pas sur
 * le réseau. `site/tests/sheet.test.js` s'occupe de ce qu'on en fait ensuite.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { drawBooklet, withSolutions } from "../js/draw.js";
import { solutionsFile } from "../js/bank.js";

const EMPTY = ".".repeat(81);
const FULL = "1".repeat(81);

/** Une banque en mémoire, de la forme que `tools/publish.py` produit. */
function fakeBank({ levels = [1, 2, 3, 4], chunks = 2, per = 6 } = {}) {
  const files = new Map();
  const index = { version: "0.1.0", generated: "2026-08-16", seed: 1, levels: [] };

  for (const number of levels) {
    const entry = { number, name: `Niveau ${number}`, count: chunks * per, chunks: [] };
    for (let position = 0; position < chunks; position += 1) {
      const file = `n${String(number).padStart(2, "0")}-${String(position).padStart(3, "0")}.json`;
      const puzzles = Array.from({ length: per }, (_, rank) => ({
        id: `l${number}c${position}p${rank}`,
        givens: 30 + rank,
        seed: 1000 + rank,
        puzzle: EMPTY,
      }));
      files.set(file, { level: number, puzzles });
      files.set(solutionsFile(file), Object.fromEntries(puzzles.map((p) => [p.id, FULL])));
      entry.chunks.push({ file, count: per });
    }
    index.levels.push(entry);
  }

  let fetches = 0;
  return {
    get fetches() {
      return fetches;
    },
    async index() {
      return index;
    },
    async chunk(file) {
      fetches += 1;
      return files.get(file);
    },
    async solutions(file) {
      fetches += 1;
      return files.get(solutionsFile(file));
    },
  };
}

test("la même graine rejoue exactement le même carnet", async () => {
  const bank = fakeBank();
  const options = { from: 1, to: 4, count: 8, seed: 4242 };
  const first = await drawBooklet(bank, options);
  const second = await drawBooklet(bank, options);
  assert.deepEqual(
    first.puzzles.map((p) => p.id),
    second.puzzles.map((p) => p.id),
  );
});

test("deux graines donnent deux carnets", async () => {
  const bank = fakeBank();
  const first = await drawBooklet(bank, { from: 1, to: 4, count: 8, seed: 1 });
  const second = await drawBooklet(bank, { from: 1, to: 4, count: 8, seed: 2 });
  assert.notDeepEqual(
    first.puzzles.map((p) => p.id),
    second.puzzles.map((p) => p.id),
  );
});

test("un carnet ne contient jamais deux fois la même grille", async () => {
  const bank = fakeBank();
  for (let seed = 0; seed < 40; seed += 1) {
    const { puzzles } = await drawBooklet(bank, { from: 1, to: 4, count: 8, seed });
    assert.equal(new Set(puzzles.map((p) => p.id)).size, puzzles.length, `graine ${seed}`);
  }
});

test("les niveaux suivent la rampe, dans l'ordre", async () => {
  const bank = fakeBank();
  const { puzzles } = await drawBooklet(bank, { from: 1, to: 4, count: 8, seed: 7 });
  assert.deepEqual(
    puzzles.map((p) => p.level),
    [1, 1, 2, 2, 3, 3, 4, 4],
  );
  assert.deepEqual(
    puzzles.map((p) => p.levelName),
    puzzles.map((p) => `Niveau ${p.level}`),
  );
});

test("les grilles déjà imprimées sont écartées", async () => {
  // Un paquet large : la réserve tient les trois tours. Ce qui se passe quand
  // elle ne tient pas est l'objet du test suivant.
  const bank = fakeBank({ levels: [1], chunks: 1, per: 20 });
  const seen = new Set();
  for (let round = 0; round < 3; round += 1) {
    const { puzzles, repeated } = await drawBooklet(bank, {
      from: 1,
      to: 1,
      count: 4,
      seed: 100 + round,
      seen,
    });
    assert.equal(repeated, false, `tour ${round}`);
    for (const puzzle of puzzles) {
      assert.ok(!seen.has(puzzle.id), `${puzzle.id} redonnée au tour ${round}`);
      seen.add(puzzle.id);
    }
  }
});

test("quand la réserve est vide, il le dit plutôt que de rendre moins", async () => {
  // Un paquet de six grilles, cinq déjà vues : il en faut quatre.
  const bank = fakeBank({ levels: [1], chunks: 1, per: 6 });
  const { puzzles } = await drawBooklet(bank, { from: 1, to: 1, count: 6, seed: 3 });
  const seen = new Set(puzzles.slice(0, 5).map((p) => p.id));

  const short = await drawBooklet(bank, { from: 1, to: 1, count: 4, seed: 9, seen });
  assert.equal(short.puzzles.length, 4);
  assert.equal(short.repeated, true);
  assert.equal(short.puzzles.filter((p) => !seen.has(p.id)).length, 1);
});

test("un carnet ne charge qu'un paquet par niveau", async () => {
  // C'est ce qui garde le coût d'une impression constant quand la banque grossit.
  const bank = fakeBank({ levels: [1, 2, 3, 4], chunks: 5, per: 20 });
  await drawBooklet(bank, { from: 1, to: 4, count: 40, seed: 5 });
  assert.equal(bank.fetches, 4);
});

test("un niveau absent de la banque est signalé", async () => {
  const bank = fakeBank({ levels: [1, 2] });
  await assert.rejects(
    () => drawBooklet(bank, { from: 1, to: 3, count: 3, seed: 1 }),
    /le niveau 3 n'est pas dans cette banque/,
  );
});

test("les solutions arrivent à part, une requête par paquet touché", async () => {
  const bank = fakeBank({ levels: [1, 2], chunks: 1, per: 6 });
  const { puzzles } = await drawBooklet(bank, { from: 1, to: 2, count: 4, seed: 11 });
  const before = bank.fetches;

  const solved = await withSolutions(bank, puzzles);
  assert.equal(bank.fetches - before, 2, "deux paquets touchés, deux fichiers de solutions");
  assert.ok(solved.every((puzzle) => puzzle.solution === FULL));
  // La grille d'origine n'a pas été modifiée en chemin.
  assert.ok(puzzles.every((puzzle) => puzzle.solution === undefined));
});
