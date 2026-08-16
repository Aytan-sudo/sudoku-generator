/**
 * La feuille imprimable : une page A4 par grille, solutions à part.
 *
 * Transcription de `src/sudoku/render/pdf.py`, fonction pour fonction. Ce
 * fichier ne décide de rien — il place aux coordonnées de `layout.js` ce que la
 * banque lui donne. Toute tentation de « faire mieux » ici ferait diverger la
 * feuille du site de celle des carnets déjà imprimés.
 */

import * as L from "./layout.js";
import { Canvas, digitBaseline, stringWidth } from "./pdf.js";

/**
 * @typedef {object} Puzzle
 * @property {string} id
 * @property {number} level
 * @property {string} levelName
 * @property {number} givens
 * @property {number} seed
 * @property {string} puzzle 81 caractères, points pour les cases vides.
 * @property {string} [solution]
 */

/** Le titre de la feuille, tel que `Rating.headline` le compose. */
export function headline(level, name) {
  return `Niveau ${level} sur ${L.LEVEL_COUNT} — ${name}`;
}

/** @param {Date} date */
export function formatDate(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}

/**
 * Dessine `cells` en un carré de côté `size`, coin bas-gauche donné.
 * @param {Canvas} canvas
 * @param {string} cells 81 caractères.
 */
export function drawGrid(
  canvas,
  cells,
  left,
  bottom,
  size,
  { thin = 0.4, thick = 1.6, frame = 2.0 } = {},
) {
  const cell = size / L.SIZE;

  canvas.setStrokeGray(L.RULE_GRAY);
  canvas.setLineWidth(thin);
  for (let step = 1; step < L.SIZE; step += 1) {
    if (step % 3) {
      const offset = step * cell;
      canvas.line(left + offset, bottom, left + offset, bottom + size);
      canvas.line(left, bottom + offset, left + size, bottom + offset);
    }
  }

  canvas.setStrokeGray(0);
  canvas.setLineWidth(thick);
  for (const step of [3, 6]) {
    const offset = step * cell;
    canvas.line(left + offset, bottom, left + offset, bottom + size);
    canvas.line(left, bottom + offset, left + size, bottom + offset);
  }

  canvas.setLineWidth(frame);
  canvas.rect(left, bottom, size, size);

  const fontSize = cell * L.DIGIT_RATIO;
  canvas.setFont(L.FONT, fontSize);
  canvas.setFillGray(0);
  for (let index = 0; index < L.CELL_COUNT; index += 1) {
    const digit = cells[index];
    if (digit === "." || digit === "0") continue;
    const centreX = left + ((index % L.SIZE) + 0.5) * cell;
    const centreY = bottom + size - (Math.floor(index / L.SIZE) + 0.5) * cell;
    canvas.drawCentredString(centreX, digitBaseline(centreY, fontSize), digit);
  }
}

/** Dix points, remplis jusqu'à `level` — l'échelle lisible d'un coup d'œil. */
export function drawGauge(canvas, level, centreX, centreY) {
  const radius = 1.9 * L.MM;
  const gap = 6.5 * L.MM;
  const start = centreX - (gap * (L.LEVEL_COUNT - 1)) / 2;

  canvas.setLineWidth(0.6);
  for (let position = 0; position < L.LEVEL_COUNT; position += 1) {
    canvas.setStrokeGray(0.45);
    canvas.setFillGray(position < level ? 0.15 : 1);
    canvas.circle(start + position * gap, centreY, radius, { stroke: true, fill: true });
  }
}

/**
 * La ligne prénom / temps — elle la remplit, et se chronomètre.
 * Un prénom connu est imprimé plutôt que réglé : il ne reste que le temps à écrire.
 */
function drawWriteInLine(canvas, baseline, player) {
  const middle = L.GRID_LEFT + L.GRID_SIZE * 0.58;
  const fields = [
    { label: "Prénom :", start: L.GRID_LEFT, end: middle - 12 * L.MM, filled: player },
    { label: "Temps :", start: middle, end: L.GRID_LEFT + L.GRID_SIZE, filled: null },
  ];

  for (const { label, start, end, filled } of fields) {
    canvas.setFont(L.FONT, 11);
    canvas.setFillGray(0.25);
    canvas.setStrokeGray(0.55);
    canvas.setLineWidth(0.5);
    canvas.drawString(start, baseline, label);

    const after = start + stringWidth(label, L.FONT, 11) + 3 * L.MM;
    if (filled) {
      canvas.setFont(L.FONT_BOLD, 11);
      canvas.setFillGray(0);
      canvas.drawString(after, baseline, filled);
    } else {
      canvas.line(after, baseline - 1.5 * L.MM, end, baseline - 1.5 * L.MM);
    }
  }
}

function drawFooter(canvas, puzzle, today) {
  canvas.setFont(L.FONT, 8);
  canvas.setFillGray(0.5);
  canvas.drawCentredString(
    L.PAGE_WIDTH / 2,
    L.FOOTER_Y,
    `n° ${puzzle.id}  ·  ${puzzle.givens} indices  ·  seed ${puzzle.seed}  ·  ${formatDate(today)}`,
  );
}

/** Une grille, seule sur sa page, telle qu'elle sera remise. */
export function drawPuzzlePage(canvas, puzzle, today, player = null) {
  canvas.setFont(L.FONT_BOLD, 16);
  canvas.setFillGray(0);
  canvas.drawCentredString(
    L.PAGE_WIDTH / 2,
    L.HEADLINE_Y,
    `Sudoku  ·  ${headline(puzzle.level, puzzle.levelName)}`,
  );

  drawGauge(canvas, puzzle.level, L.PAGE_WIDTH / 2, L.GAUGE_Y);
  drawGrid(canvas, puzzle.puzzle, L.GRID_LEFT, L.GRID_BOTTOM, L.GRID_SIZE);
  drawWriteInLine(canvas, L.NAME_Y, player);
  drawFooter(canvas, puzzle, today);
}

/**
 * Toutes les solutions, six par page, étiquetées pour être rendues à leur grille.
 * `firstPage` dit que la toile est encore vierge, donc que le premier saut de
 * page est à sauter — sinon le document s'ouvrirait sur une feuille blanche.
 */
export function drawSolutionPages(canvas, puzzles, { firstPage = false } = {}) {
  const gapX = (L.PAGE_WIDTH - L.SOLUTION_COLUMNS * L.SOLUTION_SIZE) / (L.SOLUTION_COLUMNS + 1);
  const top = 258 * L.MM;
  const gapY = 12 * L.MM;
  const caption = 7 * L.MM;

  for (let start = 0, page = 0; start < puzzles.length; start += L.SOLUTIONS_PER_PAGE, page += 1) {
    if (page || !firstPage) canvas.showPage();
    canvas.setFont(L.FONT_BOLD, 14);
    canvas.setFillGray(0);
    canvas.drawCentredString(L.PAGE_WIDTH / 2, 272 * L.MM, "Solutions");

    const batch = puzzles.slice(start, start + L.SOLUTIONS_PER_PAGE);
    batch.forEach((puzzle, position) => {
      const column = position % L.SOLUTION_COLUMNS;
      const row = Math.floor(position / L.SOLUTION_COLUMNS);
      const left = gapX + column * (L.SOLUTION_SIZE + gapX);
      const bottom = top - (row + 1) * L.SOLUTION_SIZE - row * (gapY + caption);

      drawGrid(canvas, puzzle.solution, left, bottom, L.SOLUTION_SIZE, {
        thin: 0.25,
        thick: 1.3,
        frame: 1.5,
      });
      canvas.setFont(L.FONT, 8);
      canvas.setFillGray(0.45);
      canvas.drawCentredString(
        left + L.SOLUTION_SIZE / 2,
        bottom - 5 * L.MM,
        `n° ${puzzle.id}  ·  niveau ${puzzle.level}`,
      );
    });
  }
}

/** Première page d'un carnet, avec une ligne pour que son propriétaire le réclame. */
export function drawCoverPage(canvas, cover, today, player = null) {
  // Un peu au-dessus du centre géométrique, là où un bloc de titre se lit comme
  // centré plutôt que comme ayant glissé vers le bas.
  canvas.setFont(L.FONT_BOLD, 30);
  canvas.setFillGray(0);
  canvas.drawCentredString(L.PAGE_WIDTH / 2, 182 * L.MM, cover.title);

  if (cover.subtitle) {
    canvas.setFont(L.FONT, 14);
    canvas.setFillGray(0.35);
    canvas.drawCentredString(L.PAGE_WIDTH / 2, 168 * L.MM, cover.subtitle);
  }

  canvas.setStrokeGray(0.55);
  canvas.setLineWidth(0.8);
  canvas.line(
    L.GRID_LEFT + 30 * L.MM,
    160 * L.MM,
    L.GRID_LEFT + L.GRID_SIZE - 30 * L.MM,
    160 * L.MM,
  );

  canvas.setFont(L.FONT, 14);
  canvas.setFillGray(0.25);
  canvas.setStrokeGray(0.55);
  canvas.setLineWidth(0.6);
  const label = "Carnet de :";
  const labelX = L.GRID_LEFT + 30 * L.MM;
  canvas.drawString(labelX, 128 * L.MM, label);

  const after = labelX + stringWidth(label, L.FONT, 14) + 4 * L.MM;
  if (player) {
    canvas.setFont(L.FONT_BOLD, 18);
    canvas.setFillGray(0);
    canvas.drawString(after, 128 * L.MM, player);
  } else {
    canvas.line(after, 126.5 * L.MM, L.GRID_LEFT + L.GRID_SIZE - 30 * L.MM, 126.5 * L.MM);
  }

  canvas.setFont(L.FONT, 9);
  canvas.setFillGray(0.5);
  canvas.drawCentredString(L.PAGE_WIDTH / 2, L.FOOTER_Y, formatDate(today));
}

/**
 * Le carnet : une grille par page, page de garde si demandée.
 * @param {Puzzle[]} puzzles
 * @returns {Uint8Array}
 */
export function render(puzzles, { cover = null, player = null, today = new Date() } = {}) {
  if (!puzzles.length) throw new Error("aucune grille à rendre");

  const canvas = new Canvas();
  canvas.setTitle(cover ? cover.title : "Sudoku");
  canvas.setSubject(`${puzzles.length} grille(s)`);

  if (cover) drawCoverPage(canvas, cover, today, player);
  puzzles.forEach((puzzle, position) => {
    if (position || cover) canvas.showPage();
    drawPuzzlePage(canvas, puzzle, today, player);
  });

  return canvas.save();
}

/**
 * Les solutions seules, dans un document qui reste chez l'adulte.
 * @param {Puzzle[]} puzzles
 * @returns {Uint8Array}
 */
export function renderSolutions(puzzles, { cover = null } = {}) {
  if (!puzzles.length) throw new Error("aucune grille à rendre");

  const canvas = new Canvas();
  canvas.setTitle(cover ? cover.title : "Solutions");
  canvas.setSubject(`solutions de ${puzzles.length} grille(s)`);
  drawSolutionPages(canvas, puzzles, { firstPage: true });
  return canvas.save();
}
