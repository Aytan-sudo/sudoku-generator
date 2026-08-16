"""Freeze the font metrics the site needs, straight from ReportLab's tables.

The site writes its own PDF, so nothing centres text for it: it has to know how
wide every character it prints will be. Those numbers are Adobe's, they are
already installed here with ReportLab, and copying two hundred of them by hand
is a transcription error waiting to happen. So they are generated.

    uv run python tools/metrics.py

Only Helvetica and Helvetica-Bold, and only their widths and ascent. They are
two of the fourteen fonts every PDF reader is required to own, which is why the
site can print in them without embedding a single byte of font file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.pdfbase import pdfmetrics

from sudoku.render.pdf import FONT, FONT_BOLD

TARGET = Path("site/js/metrics.js")

HEADER = """\
// Généré par tools/metrics.py — ne pas modifier à la main.
//
// Largeurs des caractères en millièmes de cadratin, indexées par octet
// WinAnsi : c'est l'encodage déclaré dans le PDF, donc `texte.charCodeAt(i)`
// tombe sur la bonne case pour tout le Latin-1, accents français compris.

"""


def widths(font: str) -> list[int]:
    """The 256 widths of ``font`` under WinAnsiEncoding, unset slots at zero."""
    return [int(width) for width in pdfmetrics.getFont(font).widths]


def render(fonts: tuple[str, ...]) -> str:
    lines = [HEADER, "export const WIDTHS = {\n"]
    for font in fonts:
        numbers = ",".join(str(width) for width in widths(font))
        lines.append(f'  "{font}": [{numbers}],\n')
    lines.append("};\n\n")

    ascent, _descent = pdfmetrics.getAscentDescent(FONT, 1000)
    lines.append(
        "export const ASCENT = "
        f"{ascent / 1000};\n"
        "/** Hauteur de capitale d'Helvetica, en parts de la taille de police.\n"
        " * Les chiffres sont bâtis dessus : c'est elle, et non la hauteur de\n"
        " * ligne, qui donne le milieu optique d'un chiffre. */\n"
    )
    return "".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère les métriques de police du site.")
    parser.add_argument("--out", type=Path, default=TARGET, help="Fichier JavaScript à écrire.")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render((FONT, FONT_BOLD)), encoding="utf-8")
    print(f"{args.out} écrit — {FONT} et {FONT_BOLD}, 256 largeurs chacune.")


if __name__ == "__main__":
    main()
