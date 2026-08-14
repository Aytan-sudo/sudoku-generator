"""Reference grids shared by the test modules.

Written nine rows at a time and folded back into the compact 81-character form,
so that a wrong digit stays easy to spot.
"""


def compact(rows: str) -> str:
    """Strip the layout of a hand-written grid, keeping only its 81 characters."""
    return "".join(rows.split())


# The sudoku used as the illustration on Wikipedia, with its solution.
CLASSIC_PUZZLE = compact("""
    530070000
    600195000
    098000060
    800060003
    400803001
    700020006
    060000280
    000419005
    000080079
""")

CLASSIC_SOLUTION = compact("""
    534678912
    672195348
    198342567
    859761423
    426853791
    713924856
    961537284
    287419635
    345286179
""")

# "Everest", the puzzle Arto Inkala published in 2012 as the hardest he could
# build. Included as a stress test: it is a proper puzzle, so the solver must
# still find exactly one solution.
HARDEST_PUZZLE = compact("""
    8........
    ..36.....
    .7..9.2..
    .5...7...
    ....457..
    ...1...3.
    ..1....68
    ..85...1.
    .9....4..
""")
