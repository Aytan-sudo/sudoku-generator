/**
 * Le PDF écrit à la main doit être un PDF.
 *
 * Ces tests visent ce qu'un coup d'œil ne rattrape pas : une table de
 * références fausse d'un octet ouvre encore dans la moitié des lecteurs, et
 * casse dans l'autre.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { Canvas, digitBaseline, stringWidth, toWinAnsi } from "../js/pdf.js";
import { ASCENT } from "../js/metrics.js";

/** Le document en texte, un octet par caractère — il est tout entier en ASCII. */
function text(bytes) {
  return String.fromCharCode(...bytes);
}

function twoPages() {
  const canvas = new Canvas();
  canvas.setFont("Helvetica", 12);
  canvas.drawString(72, 720, "Première");
  canvas.showPage();
  canvas.setFont("Helvetica-Bold", 16);
  canvas.drawCentredString(297, 400, "Seconde");
  return canvas;
}

test("le fichier s'ouvre et se ferme comme un PDF", () => {
  const document = text(twoPages().save());
  assert.ok(document.startsWith("%PDF-1.4\n"));
  assert.ok(document.endsWith("%%EOF\n"));
  assert.match(document, /trailer\n<< \/Size \d+ \/Root 1 0 R \/Info 5 0 R >>/);
});

test("chaque entrée de la table pointe sur son objet", () => {
  const document = text(twoPages().save());
  const start = Number(document.match(/startxref\n(\d+)\n%%EOF\n$/)[1]);
  assert.equal(document.slice(start, start + 4), "xref");

  const table = document.slice(start);
  const size = Number(table.match(/^xref\n0 (\d+)\n/)[1]);
  const entries = [...table.matchAll(/^(\d{10}) 00000 n $/gm)].map((match) => Number(match[1]));
  assert.equal(entries.length, size - 1);

  entries.forEach((offset, position) => {
    assert.ok(
      document.startsWith(`${position + 1} 0 obj`, offset),
      `l'objet ${position + 1} n'est pas à l'octet ${offset}`,
    );
  });
});

test("les entrées de la table font exactement vingt octets", () => {
  // Un lecteur qui lit la table au décalage plutôt qu'à la ligne dépend de ça.
  const document = text(twoPages().save());
  const table = document.slice(document.lastIndexOf("xref\n"));
  const lines = table.split("\n").slice(2, -1);
  for (const line of lines.filter((candidate) => / n $| f $/.test(candidate))) {
    assert.equal(line.length + 1, 20, JSON.stringify(line));
  }
});

test("les pages sont comptées et référencées", () => {
  const document = text(twoPages().save());
  assert.match(document, /\/Type \/Pages \/Kids \[6 0 R 8 0 R\] \/Count 2/);
  assert.equal(document.match(/\/Type \/Page[^s]/g).length, 2);
});

test("la taille de page est l'A4, au point près", () => {
  assert.match(text(twoPages().save()), /\/MediaBox \[0 0 595\.276 841\.89\]/);
});

test("le flux annonce sa vraie longueur", () => {
  const document = text(twoPages().save());
  for (const [, length, content] of document.matchAll(
    /<< \/Length (\d+) >>\nstream\n([\s\S]*?)\nendstream/g,
  )) {
    assert.equal(content.length, Number(length));
  }
});

test("une toile sans page refuse d'être écrite", () => {
  assert.throws(() => new Canvas().save(), /aucune page/);
});

// --- Le texte ---------------------------------------------------------------

test("les accents passent en WinAnsi, pas en UTF-8", () => {
  assert.deepEqual(toWinAnsi("é"), [0xe9]);
  assert.deepEqual(toWinAnsi("n°"), [0x6e, 0xb0]);
  // L'em-dash du titre : hors Latin-1, mais WinAnsi lui garde une place.
  assert.deepEqual(toWinAnsi("—"), [0x97]);
  assert.deepEqual(toWinAnsi("·"), [0xb7]);
  // Ce qui n'a pas de place devient un point d'interrogation, pas une erreur.
  assert.deepEqual(toWinAnsi("漢"), [0x3f]);
});

test("le document échappe ce qui casserait une chaîne PDF", () => {
  const canvas = new Canvas();
  canvas.setFont("Helvetica", 12);
  canvas.drawString(10, 10, "Prénom (à) \\ b");
  const document = text(canvas.save());
  assert.ok(document.includes("(Pr\\351nom \\(\\340\\) \\\\ b)"), document.slice(0, 400));
});

test("le titre du document voyage dans les métadonnées", () => {
  const canvas = new Canvas();
  canvas.setTitle("Carnet d'Émilie");
  canvas.setFont("Helvetica", 12);
  canvas.drawString(10, 10, ".");
  assert.match(text(canvas.save()), /\/Title \(Carnet d'\\311milie\)/);
});

test("la largeur d'un texte suit la police et la taille", () => {
  assert.equal(stringWidth("", "Helvetica", 12), 0);
  assert.equal(stringWidth("Hello", "Helvetica", 24), 2 * stringWidth("Hello", "Helvetica", 12));
  // Chez Helvetica, un « e » accentué occupe la place d'un « e ».
  assert.equal(stringWidth("é", "Helvetica", 12), stringWidth("e", "Helvetica", 12));
  // Le gras est plus large que le maigre sur une minuscule ronde.
  assert.ok(stringWidth("o", "Helvetica-Bold", 12) > stringWidth("o", "Helvetica", 12));
  assert.throws(() => stringWidth("a", "Times", 12), /police inconnue/);
});

test("les chiffres sont centrés sur la hauteur de capitale", () => {
  // Centrer sur la hauteur de ligne les enfoncerait : elle budgète un jambage
  // qu'aucun chiffre n'a.
  assert.equal(digitBaseline(100, 20), 100 - (ASCENT * 20) / 2);
  assert.ok(ASCENT > 0.7 && ASCENT < 0.75, `ascendante inattendue : ${ASCENT}`);
});

test("un texte centré l'est vraiment", () => {
  const canvas = new Canvas();
  canvas.setFont("Helvetica", 12);
  canvas.drawCentredString(300, 400, "abc");
  const document = text(canvas.save());
  const placed = Number(document.match(/Tf ([\d.]+) 400 Td/)[1]);
  assert.ok(
    Math.abs(placed + stringWidth("abc", "Helvetica", 12) / 2 - 300) < 0.001,
    `posé à ${placed}`,
  );
});

test("les très petits nombres ne sortent pas en notation exponentielle", () => {
  // `String(0.0000001)` donne « 1e-7 », que le PDF ne sait pas lire. L'arrondi
  // au millième les ramène à zéro avant qu'ils n'atteignent le flux.
  const canvas = new Canvas();
  canvas.setFont("Helvetica", 12);
  canvas.line(0.0000001, 1e-9, 3, 4);
  canvas.circle(1e-9, 2, 0.00004, { fill: true });
  const document = text(canvas.save());
  assert.doesNotMatch(document, /\de[+-]?\d/i);
});
