/**
 * Un hasard qu'on peut rejouer.
 *
 * Le générateur Python sème tout ce qu'il tire, et ses noms de fichiers portent
 * la graine : deux fois la même commande, deux fois le même carnet. Le site
 * tient la même promesse — la graine part dans l'URL, et le lien réimprime le
 * carnet. `Math.random()` ne se sème pas, d'où ces quinze lignes.
 *
 * Mulberry32 : un état de 32 bits, une période de 2³², une distribution qui
 * passe les tests usuels. Pour choisir des grilles dans une banque, c'est
 * largement au-dessus du nécessaire.
 */

/**
 * @param {number} seed
 * @returns {() => number} Un tirage dans [0, 1[.
 */
export function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Une graine par niveau, dérivée de celle du carnet.
 *
 * Sans quoi l'ordre des tirages dépendrait de l'ordre où les paquets reviennent
 * du réseau, et le même lien ne rendrait pas le même carnet deux fois.
 * @param {number} seed @param {number} level
 */
export function branch(seed, level) {
  return (Math.imul(seed ^ (level * 0x9e3779b9), 0x85ebca6b) ^ level) >>> 0;
}

/**
 * Une copie mélangée, par Fisher-Yates.
 * @template T @param {() => number} rng @param {readonly T[]} items @returns {T[]}
 */
export function shuffled(rng, items) {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const other = Math.floor(rng() * (index + 1));
    [copy[index], copy[other]] = [copy[other], copy[index]];
  }
  return copy;
}

/**
 * Un élément au hasard, pondéré par `weight`.
 * @template T @param {() => number} rng @param {readonly T[]} items
 * @param {(item: T) => number} weight
 */
export function weighted(rng, items, weight) {
  const total = items.reduce((sum, item) => sum + weight(item), 0);
  let target = rng() * total;
  for (const item of items) {
    target -= weight(item);
    if (target < 0) return item;
  }
  return items[items.length - 1];
}

/** Une graine neuve, prise au vrai hasard de la machine. */
export function randomSeed() {
  return crypto.getRandomValues(new Uint32Array(1))[0];
}
