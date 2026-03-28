from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core.card import Card
from freecell.core.state import GameState
from freecell.solvers.IDS import IDSSolver


def c(short_name: str) -> Card:
    return Card.from_short_name(short_name)


class IDSSolverTests(unittest.TestCase):
    def test_already_victory(self) -> None:
        state = GameState(
            cascades=(tuple(),) * 8,
            freecells=(None,) * 4,
            foundations=(13, 13, 13, 13),
        ).to_packed()

        result = IDSSolver(max_depth=50).solve(state)

        self.assertTrue(result.solved)
        self.assertEqual(result.move_count, 0)
        self.assertEqual(result.moves, ())

    def test_near_goal_one_move(self) -> None:
        state = GameState(
            cascades=((c("KS"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None,) * 4,
            foundations=(13, 13, 13, 12),
        ).to_packed()

        result = IDSSolver(max_depth=50).solve(state)

        self.assertTrue(result.solved)
        self.assertEqual(result.move_count, 1)

        current = state
        for move in result.moves:
            current = current.apply_move(move)
        self.assertTrue(current.is_victory)

    def test_replay_seed_if_solved(self) -> None:
        initial = GameState.initial(seed=1).to_packed()

        result = IDSSolver(max_depth=80, max_expansions=500_000).solve(initial)

        if result.solved:
            current = initial
            for move in result.moves:
                current = current.apply_move(move)
            self.assertTrue(current.is_victory)
        else:
            self.assertEqual(result.moves, ())

    def test_dead_end_unsolved(self) -> None:
        state = GameState(
            cascades=(
                (c("KC"),),
                (c("KD"),),
                (c("KH"),),
                (c("KS"),),
                (c("QC"),),
                (c("QD"),),
                (c("QH"),),
                (c("QS"),),
            ),
            freecells=(c("9C"), c("9D"), c("9H"), c("9S")),
            foundations=(0, 0, 0, 0),
        ).to_packed()

        result = IDSSolver(max_depth=30, max_expansions=50_000).solve(state)

        self.assertFalse(result.solved)
        self.assertEqual(result.moves, ())


if __name__ == "__main__":
    unittest.main()
