"""Grid representation and precomputed sudoku geometry.

Cells live in a flat list of 81 integers in row-major order, where 0 marks an
empty cell. Candidate sets are 9-bit masks: bit ``d - 1`` is set when digit ``d``
is still possible.

The geometry tables (units, peers, row/column/box of each cell) are built once at
import time. Every later stage — the machine solver, the human techniques, the
generator — reads them instead of recomputing indices, which is what keeps the
whole thing fast in pure Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SIZE = 9
BOX_SIZE = 3
CELL_COUNT = SIZE * SIZE
DIGITS: tuple[int, ...] = tuple(range(1, SIZE + 1))
ALL_DIGITS = (1 << SIZE) - 1
"""Mask with every digit still possible (``0b111111111``)."""

EMPTY_CHARS = frozenset(".0_")


def bit(digit: int) -> int:
    """Return the single-bit mask standing for ``digit``."""
    return 1 << (digit - 1)


def digits_from_mask(mask: int) -> tuple[int, ...]:
    """Return the digits set in ``mask``, in ascending order."""
    return tuple(digit for digit in DIGITS if mask & (1 << (digit - 1)))


# --- Geometry ---------------------------------------------------------------

ROW_OF: tuple[int, ...] = tuple(index // SIZE for index in range(CELL_COUNT))
COL_OF: tuple[int, ...] = tuple(index % SIZE for index in range(CELL_COUNT))
BOX_OF: tuple[int, ...] = tuple(
    (index // SIZE // BOX_SIZE) * BOX_SIZE + (index % SIZE) // BOX_SIZE
    for index in range(CELL_COUNT)
)

ROWS: tuple[tuple[int, ...], ...] = tuple(
    tuple(index for index in range(CELL_COUNT) if ROW_OF[index] == row) for row in range(SIZE)
)
COLS: tuple[tuple[int, ...], ...] = tuple(
    tuple(index for index in range(CELL_COUNT) if COL_OF[index] == col) for col in range(SIZE)
)
BOXES: tuple[tuple[int, ...], ...] = tuple(
    tuple(index for index in range(CELL_COUNT) if BOX_OF[index] == box) for box in range(SIZE)
)

UNITS: tuple[tuple[int, ...], ...] = ROWS + COLS + BOXES
"""The 27 units: rows 0-8, then columns 9-17, then boxes 18-26."""

UNITS_OF: tuple[tuple[int, ...], ...] = tuple(
    tuple(unit for unit, cells in enumerate(UNITS) if index in cells) for index in range(CELL_COUNT)
)
"""For each cell, the indices of the three units it belongs to."""

PEERS: tuple[frozenset[int], ...] = tuple(
    frozenset(other for unit in UNITS_OF[index] for other in UNITS[unit] if other != index)
    for index in range(CELL_COUNT)
)
"""For each cell, the 20 cells that cannot hold the same digit."""


# --- Board ------------------------------------------------------------------


class InvalidGridError(ValueError):
    """Raised when a grid cannot be built from the given input."""


@dataclass(slots=True)
class Board:
    """A sudoku grid, complete or not."""

    cells: list[int] = field(default_factory=lambda: [0] * CELL_COUNT)

    def __post_init__(self) -> None:
        if len(self.cells) != CELL_COUNT:
            raise InvalidGridError(f"une grille compte {CELL_COUNT} cases, reçu {len(self.cells)}")
        for index, digit in enumerate(self.cells):
            if not 0 <= digit <= SIZE:
                raise InvalidGridError(f"case {index} : valeur {digit} hors de 0-{SIZE}")

    # --- Construction ---

    @classmethod
    def empty(cls) -> Board:
        """Return a grid with every cell empty."""
        return cls()

    @classmethod
    def from_string(cls, text: str) -> Board:
        """Parse 81 characters, ignoring whitespace.

        Digits 1-9 fill a cell; ``.``, ``0`` and ``_`` mark it empty, so the usual
        one-line formats and pretty multi-line grids both work.
        """
        compact = "".join(text.split())
        if len(compact) != CELL_COUNT:
            raise InvalidGridError(
                f"une grille compte {CELL_COUNT} caractères, reçu {len(compact)}"
            )
        cells = []
        for position, char in enumerate(compact):
            if char in EMPTY_CHARS:
                cells.append(0)
            elif char.isdigit():
                cells.append(int(char))
            else:
                raise InvalidGridError(f"caractère {char!r} inattendu en position {position}")
        return cls(cells)

    def to_string(self) -> str:
        """Serialise to 81 characters, using ``.`` for empty cells."""
        return "".join(str(digit) if digit else "." for digit in self.cells)

    def copy(self) -> Board:
        """Return an independent copy."""
        return Board(self.cells.copy())

    # --- Access ---

    def __getitem__(self, index: int) -> int:
        return self.cells[index]

    def __setitem__(self, index: int, digit: int) -> None:
        if not 0 <= digit <= SIZE:
            raise InvalidGridError(f"valeur {digit} hors de 0-{SIZE}")
        self.cells[index] = digit

    @property
    def givens(self) -> int:
        """Number of filled cells."""
        return sum(1 for digit in self.cells if digit)

    @property
    def is_complete(self) -> bool:
        """True when no cell is left empty."""
        return all(self.cells)

    def empty_cells(self) -> tuple[int, ...]:
        """Indices of the empty cells, in reading order."""
        return tuple(index for index, digit in enumerate(self.cells) if not digit)

    # --- Rules ---

    def is_valid(self) -> bool:
        """True when no unit holds the same digit twice.

        Says nothing about solvability: an empty grid is valid.
        """
        for unit in UNITS:
            seen = 0
            for index in unit:
                digit = self.cells[index]
                if digit:
                    flag = bit(digit)
                    if seen & flag:
                        return False
                    seen |= flag
        return True

    def is_solved(self) -> bool:
        """True when the grid is both complete and valid."""
        return self.is_complete and self.is_valid()

    def candidates(self, index: int) -> int:
        """Return the mask of digits still possible at ``index``.

        A filled cell has no candidate, so the mask is 0.
        """
        if self.cells[index]:
            return 0
        used = 0
        for peer in PEERS[index]:
            digit = self.cells[peer]
            if digit:
                used |= bit(digit)
        return ALL_DIGITS & ~used

    def candidate_digits(self, index: int) -> tuple[int, ...]:
        """Return the digits still possible at ``index``."""
        return digits_from_mask(self.candidates(index))

    # --- Debug ---

    def __str__(self) -> str:
        text = self.to_string()
        return "\n".join(text[start : start + SIZE] for start in range(0, CELL_COUNT, SIZE))
