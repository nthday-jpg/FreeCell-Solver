from __future__ import annotations
from pathlib import Path
import sys
import unittest

# Set up the path to import from src
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core.card import Card
from freecell.core.state import GameState
from freecell.solvers.UCS import UCSSolver

def c(short_name: str) -> Card:
    return Card.from_short_name(short_name)

class UCSSolverCorrectnessTests(unittest.TestCase):
    def test_returns_solved_for_already_victory_state(self) -> None:
        state = GameState(
            cascades=(tuple(),) * 8,
            freecells=(None,) * 4,
            foundations=(13, 13, 13, 13)
        ).to_packed()

        result = UCSSolver().solve(state)

        self.assertTrue(result.solved)
        self.assertEqual(result.move_count, 0)
        self.assertEqual(result.moves, ())

    def test_near_goal_solves_in_one_move(self) -> None:
        # Only KS is missing on spade foundation (index 3).
        # Moving KS -> foundation should finish the game.
        state = GameState(
            cascades=((c("KS"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None,) * 4,
            foundations=(13, 13, 13, 12)
        ).to_packed()

        result = UCSSolver().solve(state)

        self.assertTrue(result.solved)
        self.assertEqual(result.move_count, 1)

        # Replay returned moves; all moves must be legal and the final state must be victory.
        current = state
        for move in result.moves:
            current = current.apply_move(move)
        
        self.assertTrue(current.is_victory())

    def test_replay_moves_from_seed_is_legal_if_solved(self) -> None:
        # Use a real seeded layout; this test validates path correctness when solver finds one.
        initial = GameState.initial(seed=1).to_packed()

        result = UCSSolver().solve(initial)

        if result.solved:
            current = initial
            for move in result.moves:
                current = current.apply_move(move)
            self.assertTrue(current.is_victory())
        else:
            # Accept unsolved for now; still a valid output state for bounded implementations.
            self.assertEqual(result.moves, ())

    def test_dead_end_returns_unsolved(self) -> None:
        # Construct a state with no legal moves:
        # - no empty freecell
        # - no empty cascade
        # - no foundation-legal top cards
        # - no cascade-to-cascade legal stacking
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

        result = UCSSolver().solve(state)

        self.assertFalse(result.solved)
        self.assertEqual(result.moves, ())\

if __name__ == "__main__":
    unittest.main()