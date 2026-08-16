/**
 * Ce que le site retient : l'adresse, et ce qui reste sur la machine.
 *
 * Dans l'URL : le niveau, le nombre de grilles, la graine. De quoi réimprimer
 * un carnet, ou l'envoyer à quelqu'un.
 *
 * Sur la machine, et nulle part ailleurs : le prénom de l'enfant et la liste
 * des grilles déjà imprimées. Le prénom ne passe pas dans l'URL — un lien se
 * partage, et le prénom d'un enfant n'a rien à y faire.
 */

const PLAYER_KEY = "sudoku.joueur";
const SEEN_KEY = "sudoku.vues";

/** Au-delà, les plus anciennes sortent. Quatre mille identifiants pèsent 36 Ko. */
const SEEN_LIMIT = 4000;

export const DEFAULTS = { from: 3, to: 3, count: 1 };

/**
 * Un magasin qui survit à un navigateur en navigation privée, où
 * `localStorage` peut lever à la lecture comme à l'écriture.
 */
const store = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch {
      return false;
    }
  },
};

function integer(value, fallback, { min = 1, max = 999 } = {}) {
  const parsed = Number.parseInt(value ?? "", 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

/**
 * Les options portées par l'adresse.
 * @param {string} [search]
 * @returns {{from: number, to: number, count: number, seed: number | null}}
 */
export function readOptions(search = globalThis.location?.search ?? "") {
  const params = new URLSearchParams(search);
  const from = integer(params.get("de"), DEFAULTS.from, { min: 1, max: 10 });
  const to = integer(params.get("a"), Math.max(from, DEFAULTS.to), { min: from, max: 10 });
  const seed = params.get("seed");
  return {
    from,
    to,
    count: integer(params.get("nb"), DEFAULTS.count, { min: 1, max: 100 }),
    seed: seed === null ? null : integer(seed, 0, { min: 0, max: 0xffffffff }),
  };
}

/** Réécrit l'adresse sans ajouter d'entrée à l'historique. */
export function writeOptions({ from, to, count, seed }) {
  const params = new URLSearchParams({ de: from, a: to, nb: count, seed });
  globalThis.history?.replaceState(null, "", `?${params}`);
}

export function loadPlayer() {
  return store.get(PLAYER_KEY) ?? "";
}

export function savePlayer(name) {
  store.set(PLAYER_KEY, name.trim());
}

/** @returns {Set<string>} Les identifiants des grilles déjà imprimées. */
export function loadSeen() {
  const raw = store.get(SEEN_KEY);
  return new Set(raw ? raw.split(",").filter(Boolean) : []);
}

/**
 * Note des grilles comme imprimées, et rend l'ensemble à jour.
 * @param {Iterable<string>} ids @returns {Set<string>}
 */
export function remember(ids) {
  const seen = [...new Set([...loadSeen(), ...ids])];
  const kept = seen.slice(Math.max(0, seen.length - SEEN_LIMIT));
  store.set(SEEN_KEY, kept.join(","));
  return new Set(kept);
}

/** Oublie tout l'historique — l'enfant a le droit de recommencer le carnet. */
export function forgetSeen() {
  store.set(SEEN_KEY, "");
  return new Set();
}
