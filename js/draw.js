/**
 * Le tirage : quelles grilles, dans quel ordre.
 *
 * C'est la seule logique que le site possède en propre, et elle est copiée sur
 * celle du générateur — `ramp()` est le port de `generator.ramp()`, aux mêmes
 * arrêtés de partage. `site/tests/ramp.test.js` la confronte à des vecteurs
 * produits par le Python, pour qu'aucune des deux ne dérive seule.
 *
 * Un carnet ne tire que dans un paquet par niveau. C'est ce qui garde le coût
 * d'une impression constant, et c'est sans conséquence : cinq cents grilles
 * d'un même niveau sont toutes également bonnes à donner.
 *
 * Les grilles déjà imprimées sont écartées, ce qui met une réserve sur la
 * reproductibilité : un lien rejoue son carnet à l'identique sur la machine qui
 * l'a produit, mais chez quelqu'un dont l'historique diffère, une grille ou
 * deux peuvent changer. Ne jamais redonner la même grille à un enfant vaut
 * mieux que rejouer un lien au caractère près.
 */

import { branch, mulberry32, shuffled, weighted } from "./rng.js";

/**
 * Répartit `count` grilles sur les niveaux de `start` à `end`.
 *
 * Un carnet qui monte convient mieux à un enfant qu'un bloc uniforme : les
 * premières pages mettent en confiance, les dernières font travailler. Les
 * niveaux se partagent à parts égales, le reste allant vers le bas — un carnet
 * est un meilleur endroit pour commencer doucement que pour finir brutalement.
 *
 * @param {number} start @param {number} end @param {number} count
 * @returns {number[]}
 */
export function ramp(start, end, count) {
  if (start > end) throw new Error(`le niveau de départ (${start}) dépasse celui d'arrivée (${end})`);
  if (count < 1) throw new Error("count doit valoir au moins 1");

  const levels = [];
  for (let level = start; level <= end; level += 1) levels.push(level);

  if (count <= levels.length) {
    // Trop peu de grilles pour visiter chaque niveau : on échantillonne
    // régulièrement l'intervalle. Arrondi au demi supérieur, comme en Python.
    const step = (levels.length - 1) / Math.max(count - 1, 1);
    return Array.from({ length: count }, (_, position) =>
      levels[Math.floor(position * step + 0.5)],
    );
  }

  const base = Math.floor(count / levels.length);
  const extra = count % levels.length;
  return levels.flatMap((level, position) =>
    Array.from({ length: base + (position < extra ? 1 : 0) }, () => level),
  );
}

/**
 * @typedef {object} Drawn
 * @property {import("./sheet.js").Puzzle[]} puzzles
 * @property {boolean} repeated Vrai si la réserve de grilles neuves était trop
 *   courte et que des grilles déjà imprimées ont dû resservir.
 */

/**
 * Tire un carnet dans la banque.
 *
 * @param {import("./bank.js").Bank} bank
 * @param {{from: number, to: number, count: number, seed: number, seen?: Set<string>}} options
 * @returns {Promise<Drawn>}
 */
export async function drawBooklet(bank, { from, to, count, seed, seen = new Set() }) {
  const index = await bank.index();
  const byNumber = new Map(index.levels.map((level) => [level.number, level]));

  const wanted = ramp(from, to, count);
  const needed = new Map();
  for (const level of wanted) needed.set(level, (needed.get(level) ?? 0) + 1);

  let repeated = false;
  const drawn = new Map();

  await Promise.all(
    [...needed].map(async ([number, share]) => {
      const level = byNumber.get(number);
      if (!level) throw new Error(`le niveau ${number} n'est pas dans cette banque`);

      // La graine dérive du niveau, donc l'ordre d'arrivée des paquets ne
      // change rien au tirage.
      const rng = mulberry32(branch(seed, number));
      const chunk = weighted(rng, level.chunks, (candidate) => candidate.count);
      const { puzzles } = await bank.chunk(chunk.file);
      const order = shuffled(rng, puzzles);

      const fresh = order.filter((entry) => !seen.has(entry.id));
      const chosen = fresh.slice(0, share);
      if (chosen.length < share) {
        repeated = true;
        chosen.push(...order.filter((entry) => seen.has(entry.id)).slice(0, share - chosen.length));
      }

      drawn.set(
        number,
        chosen.map((entry) => ({
          ...entry,
          level: number,
          levelName: level.name,
          file: chunk.file,
        })),
      );
    }),
  );

  const remaining = new Map([...drawn].map(([number, entries]) => [number, [...entries]]));
  return { puzzles: wanted.map((level) => remaining.get(level).shift()), repeated };
}

/**
 * Ajoute leur solution aux grilles données, un fichier par paquet touché.
 * @param {import("./bank.js").Bank} bank
 * @param {import("./sheet.js").Puzzle[]} puzzles
 * @returns {Promise<import("./sheet.js").Puzzle[]>}
 */
export async function withSolutions(bank, puzzles) {
  const files = [...new Set(puzzles.map((puzzle) => puzzle.file))];
  const loaded = new Map(
    await Promise.all(files.map(async (file) => [file, await bank.solutions(file)])),
  );
  return puzzles.map((puzzle) => ({ ...puzzle, solution: loaded.get(puzzle.file)[puzzle.id] }));
}
