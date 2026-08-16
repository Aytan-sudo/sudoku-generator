/**
 * Les millimètres de la feuille, transcrits de `src/sudoku/render/pdf.py`.
 *
 * Rien ici n'est un choix : ce sont les constantes du générateur Python,
 * recopiées telles quelles. Le PDF partage son repère avec ReportLab — origine
 * en bas à gauche, unité le point — donc la transcription est littérale, sans
 * axe à retourner. `tests/test_site_layout.py` compare les deux fichiers et
 * échoue si l'un bouge sans l'autre.
 */

/** Un millimètre, en points PostScript. */
export const MM = 72 / 25.4;

export const FONT = "Helvetica";
export const FONT_BOLD = "Helvetica-Bold";

export const PAGE_WIDTH = 210 * MM;
export const PAGE_HEIGHT = 297 * MM;

/** 20 mm par case. Délibérément grand : un enfant de neuf ans qui écrit un
 * chiffre au crayon, et qui l'efface, a besoin de la place. */
export const GRID_SIZE = 180 * MM;

export const GRID_LEFT = (PAGE_WIDTH - GRID_SIZE) / 2;
export const GRID_TOP = 242 * MM;
export const GRID_BOTTOM = GRID_TOP - GRID_SIZE;

export const HEADLINE_Y = 270 * MM;
export const GAUGE_Y = 254 * MM;
export const NAME_Y = 46 * MM;
export const FOOTER_Y = 18 * MM;

/** Taille du chiffre, en part de la case. */
export const DIGIT_RATIO = 0.55;

/** Séparateurs de cases à 40 % d'encre : présents, jamais en concurrence
 * avec les chiffres. */
export const RULE_GRAY = 0.6;

export const SOLUTIONS_PER_PAGE = 6;
export const SOLUTION_SIZE = 70 * MM;
export const SOLUTION_COLUMNS = 2;

/** Le nombre d'échelons, qui donne aussi le nombre de points de la jauge. */
export const LEVEL_COUNT = 10;

/** Côté d'une grille, en cases. */
export const SIZE = 9;
export const CELL_COUNT = SIZE * SIZE;
