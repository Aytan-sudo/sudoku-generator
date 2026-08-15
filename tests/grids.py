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

# One grid per advanced technique, each found by digging until the human solver
# reported that exact technique as its ceiling. So each is a grid the technique
# is genuinely *needed* for: every cheaper technique in the catalogue runs out on
# it, and nothing more expensive is called upon.
#
# Found with tools/find_fixtures.py, then frozen here so the tests stay fast and
# deterministic.
NEEDS_TECHNIQUE: dict[str, str] = {
    "pointing": compact("""
    31....9..
    ....2.1..
    ...138...
    ....8.5..
    685....3.
    ..7....2.
    .6.2....9
    1..4....7
    ..3.562..
    """),
    "claiming": compact("""
    87..15...
    ..1.89.6.
    ..6..7..5
    3.....64.
    ..5...2..
    1.28....3
    .18.6...4
    52.......
    64...1.2.
    """),
    "naked_pair": compact("""
    .....54..
    ..9..3...
    18.4...3.
    9.4...8..
    .....174.
    .6......5
    ....4.95.
    7...26...
    89..1...4
    """),
    "hidden_pair": compact("""
    9.12.65..
    .4..13.2.
    ......9..
    .6.....8.
    .........
    31.8..679
    ...3..21.
    ..4..9..3
    .7......8
    """),
    "naked_triple": compact("""
    ..9.23...
    ..4....6.
    1..7....2
    2.71.865.
    9....5...
    851.7....
    7.2.8.9..
    4..51..7.
    .....71..
    """),
    "hidden_triple": compact("""
    ..187...9
    8.4...76.
    ..9..4..1
    .....26.7
    ..6...1..
    .....7.54
    .6..41..2
    1..5...4.
    4.......8
    """),
    "x_wing": compact("""
    47.......
    9..3....8
    8.6.2..4.
    3......8.
    ..7...3..
    2.9.8.1..
    ..1.92...
    ...6...15
    6...1.9..
    """),
    "xy_wing": compact("""
    ...2..34.
    1.2..68.5
    ........1
    .6...31..
    7....2...
    .1.6...72
    ...58..1.
    5....94..
    .8....9..
    """),
}
