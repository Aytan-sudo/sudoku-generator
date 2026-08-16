/**
 * Le câblage : le formulaire d'un côté, le PDF de l'autre.
 *
 * L'aperçu n'imite pas le document, c'est le document — le PDF est produit,
 * puis affiché par la visionneuse du navigateur. Il n'y a donc qu'un seul
 * moteur de rendu dans ce site, et ce qu'on voit est au bit près ce qu'on
 * télécharge.
 */

import { Bank } from "./bank.js";
import { drawBooklet, withSolutions } from "./draw.js";
import { LEVEL_COUNT } from "./layout.js";
import { randomSeed } from "./rng.js";
import { render, renderSolutions } from "./sheet.js";
import {
  DEFAULTS,
  forgetSeen,
  loadPlayer,
  loadSeen,
  readOptions,
  remember,
  savePlayer,
  writeOptions,
} from "./state.js";

/** Les familles de l'échelle, telles qu'elles se présentent honnêtement. */
const FAMILIES = [
  { label: "Pour débuter", from: 1, to: 6 },
  { label: "Pour s'entraîner", from: 7, to: 9 },
  { label: "Hors catalogue", from: 10, to: 10 },
];

const BEYOND = 10;

const bank = new Bank();
const view = {
  form: document.getElementById("options"),
  levels: document.getElementById("niveaux"),
  showBeyond: document.getElementById("montrer-dix"),
  levelField: document.getElementById("champ-niveau"),
  bookletField: document.getElementById("champ-carnet"),
  from: document.getElementById("de"),
  to: document.getElementById("a"),
  count: document.getElementById("nombre"),
  countWord: document.getElementById("nombre-mot"),
  player: document.getElementById("joueur"),
  reroll: document.getElementById("tirer"),
  download: document.getElementById("telecharger"),
  downloadSolutions: document.getElementById("telecharger-solutions"),
  viewer: document.getElementById("visionneuse"),
  status: document.getElementById("etat"),
  seenCount: document.getElementById("deja"),
  forget: document.getElementById("oublier"),
  bankLine: document.getElementById("banque"),
};

let index = null;
let seen = loadSeen();
let seed = randomSeed();
let current = [];
let previewUrl = null;

/** Un nom de fichier sans accent ni espace, comme `_slug` côté Python. */
function slug(text) {
  return text
    .normalize("NFKD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function stamp(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}`;
}

function plural(count, word) {
  return count > 1 ? `${word}s` : word;
}

/** Ce que le formulaire dit, à un instant. */
function options() {
  const booklet = view.form.mode.value === "carnet";
  const chosen = Number(view.form.niveau?.value) || DEFAULTS.from;
  const from = booklet ? Number(view.from.value) : chosen;
  const to = booklet ? Math.max(from, Number(view.to.value)) : chosen;
  return { booklet, from, to, count: Math.max(1, Number(view.count.value) || 1) };
}

function gauge(level) {
  const dots = Array.from(
    { length: LEVEL_COUNT },
    (_, position) => `<i class="${position < level ? "plein" : ""}"></i>`,
  ).join("");
  return `<span class="jauge" aria-hidden="true">${dots}</span>`;
}

function buildLevels(selected) {
  const visible = index.levels.filter(
    (level) => level.number !== BEYOND || view.showBeyond.checked,
  );
  // Le niveau retenu peut venir de disparaître — on décoche « montrer le
  // niveau 10 » alors qu'il était choisi. Sans repli, plus aucune tuile ne
  // serait cochée et le tirage partirait sur un niveau zéro.
  const chosen = visible.some((level) => level.number === selected)
    ? selected
    : visible[visible.length - 1].number;

  view.levels.innerHTML = FAMILIES.map((family) => {
    const rows = visible.filter(
      (level) => level.number >= family.from && level.number <= family.to,
    );
    if (!rows.length) return "";
    const tiles = rows
      .map(
        (level) => `
        <label class="tuile">
          <input type="radio" name="niveau" value="${level.number}"
                 ${level.number === chosen ? "checked" : ""} />
          <span>
            <span class="rang">${level.number}</span>
            <span class="nom">${level.name}</span>
            ${gauge(level.number)}
          </span>
        </label>`,
      )
      .join("");
    return `<p class="famille">${family.label}</p>${tiles}`;
  }).join("");
}

function buildSelects() {
  const choices = index.levels
    .map((level) => `<option value="${level.number}">${level.number} — ${level.name}</option>`)
    .join("");
  view.from.innerHTML = choices;
  view.to.innerHTML = choices;
}

function fileName(kind, { booklet, from, to, count }) {
  const parts = [booklet ? "carnet" : `sudoku-niveau${from}${to > from ? `-${to}` : ""}`];
  const player = slug(view.player.value);
  if (player) parts.push(player);
  if (!booklet && count === 1 && current.length) {
    parts.push(current[0].id);
  } else {
    parts.push(stamp(new Date()), String(seed));
  }
  if (kind === "solutions") parts.push("solutions");
  return `${parts.join("-")}.pdf`;
}

function cover(chosen) {
  if (!chosen.booklet) return null;
  const name = (number) => index.levels.find((level) => level.number === number)?.name ?? "";
  return {
    title: "Carnet de sudokus",
    subtitle:
      `${chosen.count} ${plural(chosen.count, "grille")}, du niveau ${chosen.from}` +
      ` « ${name(chosen.from)} » au niveau ${chosen.to} « ${name(chosen.to)} »`,
  };
}

function say(message) {
  view.status.textContent = message;
}

function updateSeenLine() {
  view.seenCount.textContent = seen.size
    ? `${seen.size} ${plural(seen.size, "grille")} ${plural(seen.size, "déjà imprimée")} ` +
      "depuis ce navigateur. Elles ne reviendront pas tant qu'il en reste d'autres."
    : "Aucune grille imprimée depuis ce navigateur pour l'instant.";
}

async function refresh() {
  const chosen = options();
  view.bookletField.hidden = !chosen.booklet;
  view.levelField.hidden = chosen.booklet;
  view.countWord.textContent = plural(chosen.count, "grille");

  say("Tirage…");
  view.download.setAttribute("aria-disabled", "true");
  view.downloadSolutions.disabled = true;

  try {
    const { puzzles, repeated } = await drawBooklet(bank, { ...chosen, seed, seen });
    current = puzzles;

    const player = view.player.value.trim();
    const bytes = render(puzzles, { cover: cover(chosen), player: player || null });
    const blob = new Blob([bytes], { type: "application/pdf" });

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(blob);
    view.viewer.src = previewUrl;
    view.download.href = previewUrl;
    view.download.download = fileName("grilles", chosen);
    view.download.removeAttribute("aria-disabled");
    view.downloadSolutions.disabled = false;

    writeOptions({ ...chosen, seed });

    const pages = puzzles.length + (chosen.booklet ? 1 : 0);
    say(
      `${puzzles.length} ${plural(puzzles.length, "grille")}, ${pages} pages.` +
        (repeated ? " La réserve de grilles neuves est épuisée : certaines resservent." : ""),
    );
  } catch (error) {
    console.error(error);
    say(`Le tirage a échoué : ${error.message}`);
  }
}

async function downloadSolutions() {
  if (!current.length) return;
  view.downloadSolutions.disabled = true;
  say("Préparation des solutions…");
  try {
    const withAnswers = await withSolutions(bank, current);
    const bytes = renderSolutions(withAnswers);
    const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName("solutions", options());
    link.click();
    // Laisse au navigateur le temps de démarrer le téléchargement avant de
    // reprendre l'objet.
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    say("Solutions téléchargées, dans un fichier à part.");
  } catch (error) {
    console.error(error);
    say(`Les solutions n'ont pas pu être écrites : ${error.message}`);
  } finally {
    view.downloadSolutions.disabled = false;
  }
}

async function boot() {
  try {
    index = await bank.index();
  } catch (error) {
    console.error(error);
    say("La banque de grilles n'a pas pu être chargée.");
    return;
  }

  const total = index.levels.reduce((sum, level) => sum + level.count, 0);
  view.bankLine.textContent =
    `Banque du ${index.generated}, ${total.toLocaleString("fr-FR")} grilles,` +
    ` graine ${index.seed} — générateur ${index.version}.`;

  const restored = readOptions();
  seed = restored.seed ?? randomSeed();
  if (restored.from === BEYOND || restored.to === BEYOND) view.showBeyond.checked = true;

  buildSelects();
  buildLevels(restored.from);
  view.from.value = String(restored.from);
  view.to.value = String(restored.to);
  view.count.value = String(restored.count);
  view.player.value = loadPlayer();
  if (restored.to > restored.from) view.form.mode.value = "carnet";

  updateSeenLine();

  // Le prénom se rejoue à la frappe, avec un temps mort : l'aperçu suit, et il
  // est à jour avant que la main n'ait atteint le bouton.
  let pending = null;
  view.form.addEventListener("input", (event) => {
    if (event.target !== view.player) return;
    savePlayer(view.player.value);
    clearTimeout(pending);
    pending = setTimeout(refresh, 350);
  });

  view.form.addEventListener("change", (event) => {
    if (event.target === view.player) return;
    if (event.target === view.showBeyond) {
      buildLevels(options().from);
      refresh();
      return;
    }
    if (event.target.name === "mode" && view.form.mode.value === "carnet") {
      // Un carnet d'une seule grille sur un seul niveau n'aurait aucun sens :
      // le mode arrive avec les valeurs par défaut de la commande `carnet`.
      const top = index.levels[index.levels.length - 1].number;
      if (Number(view.to.value) <= Number(view.from.value)) {
        view.to.value = String(Math.min(Number(view.from.value) + 3, top));
      }
      if (Number(view.count.value) < 2) view.count.value = "20";
    }
    refresh();
  });

  // Une grille compte comme donnée quand elle part sur le disque, pas quand
  // elle passe dans l'aperçu — sinon tâtonner dans le formulaire consommerait
  // la banque.
  view.download.addEventListener("click", () => {
    seen = remember(current.map((puzzle) => puzzle.id));
    updateSeenLine();
  });
  view.reroll.addEventListener("click", () => {
    seed = randomSeed();
    refresh();
  });
  view.downloadSolutions.addEventListener("click", downloadSolutions);
  view.forget.addEventListener("click", () => {
    seen = forgetSeen();
    updateSeenLine();
    say("Historique effacé.");
  });
  view.form.addEventListener("submit", (event) => event.preventDefault());

  await refresh();
}

boot();
