/**
 * L'accès à la banque : un index, des paquets, et les solutions à part.
 *
 * `tools/publish.py` a découpé la banque en paquets de 500 grilles d'un même
 * niveau, chacun doublé d'un fichier de solutions. Le site lit l'index, tire un
 * paquet, et n'en charge pas d'autre : imprimer une grille coûte une vingtaine
 * de kilo-octets, que la banque en contienne cinq mille ou deux cent mille.
 *
 * Les solutions ne sont demandées que si un adulte clique pour les avoir. Rien
 * n'est caché — tout ce qui est servi est public — mais la page que l'enfant a
 * sous les yeux n'a jamais tenu la réponse.
 */

/**
 * @typedef {object} ChunkRef
 * @property {string} file
 * @property {number} count
 *
 * @typedef {object} LevelEntry
 * @property {number} number
 * @property {string} name
 * @property {number} count
 * @property {ChunkRef[]} chunks
 *
 * @typedef {object} Index
 * @property {string} version
 * @property {string} generated
 * @property {number} seed
 * @property {LevelEntry[]} levels
 */

/** Le nom du fichier de solutions qui accompagne un paquet. */
export function solutionsFile(file) {
  return file.replace(/\.json$/, "-sol.json");
}

export class Bank {
  #base;
  #index = null;
  #chunks = new Map();

  /** @param {string} base Dossier des fichiers, terminé par une barre. */
  constructor(base = "banque/") {
    this.#base = base;
  }

  async #fetch(file) {
    const response = await fetch(this.#base + file);
    if (!response.ok) {
      throw new Error(`${file} : ${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  /** @returns {Promise<Index>} */
  async index() {
    this.#index ??= await this.#fetch("index.json");
    return this.#index;
  }

  /**
   * Un paquet de grilles, gardé en mémoire une fois chargé.
   * @param {string} file @returns {Promise<{level: number, puzzles: object[]}>}
   */
  async chunk(file) {
    if (!this.#chunks.has(file)) {
      // La promesse est mise en cache, pas seulement son résultat : deux
      // demandes du même paquet pendant qu'il arrive ne font qu'une requête.
      this.#chunks.set(file, this.#fetch(file));
    }
    return this.#chunks.get(file);
  }

  /**
   * Les solutions d'un paquet, indexées par identifiant.
   * @param {string} file Le nom du paquet de grilles, pas celui des solutions.
   * @returns {Promise<Record<string, string>>}
   */
  async solutions(file) {
    const key = solutionsFile(file);
    if (!this.#chunks.has(key)) {
      this.#chunks.set(
        key,
        this.#fetch(key).then((payload) => payload.solutions),
      );
    }
    return this.#chunks.get(key);
  }
}
