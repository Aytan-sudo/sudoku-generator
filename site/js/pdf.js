/**
 * Un écrivain PDF taillé pour une seule feuille : celle de `render/pdf.py`.
 *
 * Le document à produire ne contient que des traits, un rectangle, des cercles
 * et du texte en Helvetica — laquelle fait partie des quatorze polices que tout
 * lecteur de PDF possède, donc pas un octet de fichier de police à embarquer.
 * Ce qui restait tenait en deux cents lignes, contre les cent cinquante kilos
 * gzippés d'une bibliothèque : quatre fois la banque chargée pour imprimer la
 * première grille.
 *
 * L'API imite volontairement celle du `Canvas` de ReportLab — mêmes noms, mêmes
 * arguments, même repère (origine en bas à gauche, unité le point). `sheet.js`
 * se lit alors ligne pour ligne à côté de `render/pdf.py`.
 *
 * Les flux ne sont pas compressés. Une page pèse environ quatre kilo-octets, un
 * carnet de vingt grilles moins de cent : `CompressionStream` rendrait l'API
 * asynchrone pour économiser ce que le disque ne compte plus.
 */

import { ASCENT, WIDTHS } from "./metrics.js";

/** Poignée de Bézier approchant un quart de cercle, à 2 pour 10 000 près. */
const KAPPA = 0.5523;

/**
 * Caractères hors Latin-1 que WinAnsi place quand même, aux codes 128 à 159.
 * L'em-dash est le seul dont la feuille ait besoin — le titre l'utilise — mais
 * une apostrophe typographique dans un prénom collé depuis ailleurs ne doit pas
 * casser le rendu pour autant.
 */
const WIN_ANSI_EXTRAS = new Map([
  [0x20ac, 0x80],
  [0x201a, 0x82],
  [0x2039, 0x8b],
  [0x2018, 0x91],
  [0x2019, 0x92],
  [0x201c, 0x93],
  [0x201d, 0x94],
  [0x2022, 0x95],
  [0x2013, 0x96],
  [0x2014, 0x97],
  [0x203a, 0x9b],
  [0x2026, 0x85],
]);

/**
 * Le texte en octets WinAnsi, l'encodage déclaré par les polices du document.
 * Ce qui n'y figure pas devient un point d'interrogation : mieux vaut un
 * prénom approximatif qu'un PDF illisible.
 * @param {string} text
 * @returns {number[]}
 */
export function toWinAnsi(text) {
  const out = [];
  for (const char of text) {
    const code = char.codePointAt(0);
    if (code < 0x100) {
      out.push(code);
    } else {
      out.push(WIN_ANSI_EXTRAS.get(code) ?? 0x3f);
    }
  }
  return out;
}

/**
 * Largeur du texte, dans l'unité de `size`.
 * @param {string} text
 * @param {string} font
 * @param {number} size
 */
export function stringWidth(text, font, size) {
  const widths = WIDTHS[font];
  if (!widths) throw new Error(`police inconnue : ${font}`);
  let total = 0;
  for (const code of toWinAnsi(text)) total += widths[code];
  return (total * size) / 1000;
}

/**
 * Ligne de base plaçant le milieu optique d'un chiffre à `centreY`.
 *
 * Centrer sur la hauteur de ligne l'enfoncerait d'un dixième de sa taille :
 * cette hauteur budgète un jambage qu'aucun chiffre n'a. Les chiffres
 * d'Helvetica montent à la hauteur de capitale, c'est donc d'elle que se déduit
 * la ligne de base.
 * @param {number} centreY
 * @param {number} fontSize
 */
export function digitBaseline(centreY, fontSize) {
  return centreY - (ASCENT * fontSize) / 2;
}

/** Un nombre tel que le PDF l'accepte : jamais de notation exponentielle. */
function num(value) {
  const rounded = Math.round(value * 1000) / 1000;
  return Object.is(rounded, -0) ? "0" : String(rounded);
}

/** Une chaîne littérale PDF, tout ce qui dépasse l'ASCII passé en octal. */
function literal(text) {
  let out = "(";
  for (const code of toWinAnsi(text)) {
    if (code === 0x28 || code === 0x29 || code === 0x5c) {
      out += `\\${String.fromCharCode(code)}`;
    } else if (code < 0x20 || code > 0x7e) {
      out += `\\${code.toString(8).padStart(3, "0")}`;
    } else {
      out += String.fromCharCode(code);
    }
  }
  return `${out})`;
}

/**
 * Une toile qui accumule des pages, et les rend en PDF.
 *
 * Comme chez ReportLab, la première page est ouverte d'office, `showPage()`
 * ferme la courante et en ouvre une autre, et `save()` ferme la dernière.
 */
export class Canvas {
  #pages = [];
  #ops = [];
  #font = "Helvetica";
  #size = 12;
  #title = "Sudoku";
  #subject = "";

  /** @param {{width?: number, height?: number}} [options] */
  constructor({ width = 595.2755905511812, height = 841.8897637795276 } = {}) {
    this.width = width;
    this.height = height;
  }

  /** @param {string} title */
  setTitle(title) {
    this.#title = title;
  }

  /** @param {string} subject */
  setSubject(subject) {
    this.#subject = subject;
  }

  /** Termine la page courante et en commence une neuve. */
  showPage() {
    this.#pages.push(this.#ops.join("\n"));
    this.#ops = [];
  }

  /** Nombre de pages déjà closes, plus celle en cours si elle porte du dessin. */
  get pageCount() {
    return this.#pages.length + (this.#ops.length ? 1 : 0);
  }

  /** @param {number} width */
  setLineWidth(width) {
    this.#ops.push(`${num(width)} w`);
  }

  /** @param {number} gray 0 pour le noir, 1 pour le blanc. */
  setStrokeGray(gray) {
    this.#ops.push(`${num(gray)} G`);
  }

  /** @param {number} gray */
  setFillGray(gray) {
    this.#ops.push(`${num(gray)} g`);
  }

  /**
   * @param {number} x1 @param {number} y1 @param {number} x2 @param {number} y2
   */
  line(x1, y1, x2, y2) {
    this.#ops.push(`${num(x1)} ${num(y1)} m ${num(x2)} ${num(y2)} l S`);
  }

  /**
   * @param {number} x @param {number} y @param {number} width @param {number} height
   * @param {{stroke?: boolean, fill?: boolean}} [options]
   */
  rect(x, y, width, height, { stroke = true, fill = false } = {}) {
    const paint = fill && stroke ? "B" : fill ? "f" : "S";
    this.#ops.push(`${num(x)} ${num(y)} ${num(width)} ${num(height)} re ${paint}`);
  }

  /**
   * @param {number} centreX @param {number} centreY @param {number} radius
   * @param {{stroke?: boolean, fill?: boolean}} [options]
   */
  circle(centreX, centreY, radius, { stroke = true, fill = false } = {}) {
    const handle = radius * KAPPA;
    const [x, y, r, k] = [centreX, centreY, radius, handle];
    const paint = fill && stroke ? "B" : fill ? "f" : "S";
    this.#ops.push(
      [
        `${num(x + r)} ${num(y)} m`,
        `${num(x + r)} ${num(y + k)} ${num(x + k)} ${num(y + r)} ${num(x)} ${num(y + r)} c`,
        `${num(x - k)} ${num(y + r)} ${num(x - r)} ${num(y + k)} ${num(x - r)} ${num(y)} c`,
        `${num(x - r)} ${num(y - k)} ${num(x - k)} ${num(y - r)} ${num(x)} ${num(y - r)} c`,
        `${num(x + k)} ${num(y - r)} ${num(x + r)} ${num(y - k)} ${num(x + r)} ${num(y)} c`,
        `h ${paint}`,
      ].join(" "),
    );
  }

  /** @param {string} font @param {number} size */
  setFont(font, size) {
    if (!WIDTHS[font]) throw new Error(`police inconnue : ${font}`);
    this.#font = font;
    this.#size = size;
  }

  /** @param {number} x @param {number} y @param {string} text */
  drawString(x, y, text) {
    const name = this.#font === "Helvetica-Bold" ? "F2" : "F1";
    this.#ops.push(
      `BT /${name} ${num(this.#size)} Tf ${num(x)} ${num(y)} Td ${literal(text)} Tj ET`,
    );
  }

  /** @param {number} x @param {number} y @param {string} text */
  drawCentredString(x, y, text) {
    this.drawString(x - this.stringWidth(text) / 2, y, text);
  }

  /** Largeur du texte dans la police courante. @param {string} text */
  stringWidth(text) {
    return stringWidth(text, this.#font, this.#size);
  }

  /**
   * Le document entier, prêt à être écrit ou passé à un `Blob`.
   * @returns {Uint8Array}
   */
  save() {
    if (this.#ops.length) this.showPage();
    if (!this.#pages.length) throw new Error("aucune page à écrire");

    // Numérotation fixée d'avance : elle évite de tenir un graphe de références
    // pour un document dont la forme ne varie pas.
    const CATALOG = 1;
    const PAGES = 2;
    const FIRST_PAGE = 6;
    const pageNumber = (index) => FIRST_PAGE + 2 * index;
    const kids = this.#pages.map((_, index) => `${pageNumber(index)} 0 R`).join(" ");
    const box = `[0 0 ${num(this.width)} ${num(this.height)}]`;

    const objects = new Map();
    objects.set(CATALOG, `<< /Type /Catalog /Pages ${PAGES} 0 R >>`);
    objects.set(PAGES, `<< /Type /Pages /Kids [${kids}] /Count ${this.#pages.length} >>`);
    objects.set(3, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
    objects.set(
      4,
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    );
    objects.set(5, `<< /Title ${literal(this.#title)} /Subject ${literal(this.#subject)} >>`);

    this.#pages.forEach((content, index) => {
      const self = pageNumber(index);
      objects.set(
        self,
        `<< /Type /Page /Parent ${PAGES} 0 R /MediaBox ${box}` +
          ` /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >>` +
          ` /Contents ${self + 1} 0 R >>`,
      );
      objects.set(self + 1, `<< /Length ${content.length} >>\nstream\n${content}\nendstream`);
    });

    let file = "%PDF-1.4\n";
    const offsets = new Map();
    for (const [number, body] of [...objects].sort(([a], [b]) => a - b)) {
      offsets.set(number, file.length);
      file += `${number} 0 obj\n${body}\nendobj\n`;
    }

    const size = objects.size + 1;
    const start = file.length;
    file += `xref\n0 ${size}\n0000000000 65535 f \n`;
    for (let number = 1; number < size; number += 1) {
      file += `${String(offsets.get(number)).padStart(10, "0")} 00000 n \n`;
    }
    file += `trailer\n<< /Size ${size} /Root ${CATALOG} 0 R /Info 5 0 R >>\n`;
    file += `startxref\n${start}\n%%EOF\n`;

    // Tout ce qui dépassait l'ASCII a été échappé en octal, donc un caractère
    // vaut un octet et les positions notées dans la table valent aussi bien
    // pour la chaîne que pour le fichier.
    const bytes = new Uint8Array(file.length);
    for (let index = 0; index < file.length; index += 1) {
      bytes[index] = file.charCodeAt(index) & 0xff;
    }
    return bytes;
  }
}
