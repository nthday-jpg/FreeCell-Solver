from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core.card import Card
from freecell.core.card import card_to_code, code_to_card
from freecell.core import GameState, Move
from freecell.core.packed_state import PackedState


def c(short_name: str) -> Card:
    return Card.from_short_name(short_name)


class GameStateTests(unittest.TestCase):
    def test_card_code_roundtrip(self) -> None:
        samples = ["AC", "10D", "QH", "KS"]
        for short_name in samples:
            card = c(short_name)
            self.assertEqual(code_to_card(card_to_code(card)), card)

    def test_state_to_packed_roundtrip(self) -> None:
        state = GameState(
            cascades=(
                (c("8C"), c("7D"), c("6C")),
                (c("9H"),),
                tuple(),
                (c("AS"), c("2H")),
                tuple(),
                (c("KD"),),
                tuple(),
                tuple(),
            ),
            freecells=(c("4S"), None, c("5D"), None),
            foundations=(1, 3, 2, 0),
        )

        packed = state.to_packed()
        unpacked = GameState.from_packed(packed)
        self.assertEqual(unpacked, state)

    def test_initial_generates_valid_layout_and_is_seed_stable(self) -> None:
        state_a = GameState.initial(seed=1)
        state_b = GameState.initial(seed=1)

        self.assertEqual(state_a, state_b)
        self.assertEqual(len(state_a.cascades), 8)
        self.assertEqual([len(cascade) for cascade in state_a.cascades], [7, 7, 7, 7, 6, 6, 6, 6])

    def test_foundation_helpers_and_counts(self) -> None:
        state = GameState(
            cascades=((c("AS"),), tuple(), tuple(), (c("2D"),), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, c("3C"), None, c("4H")),
            foundations=(1, 2, 3, 4),
        )

        self.assertEqual(state.foundation_rank("C"), 1)
        self.assertEqual(state.foundation_rank("D"), 2)
        self.assertEqual(state.empty_freecell_count(), 2)
        self.assertEqual(state.empty_cascade_count(), 6)
        self.assertEqual(state.cascade_top(0), c("AS"))
        self.assertIsNone(state.cascade_top(1))
        self.assertEqual(state.foundation_summary(), {"C": 1, "D": 2, "H": 3, "S": 4})
        self.assertFalse(state.foundation_complete())
        self.assertTrue(GameState(cascades=(tuple(),) * 8, foundations=(13, 13, 13, 13)).foundation_complete())

    def test_packed_state_victory_helpers(self) -> None:
        incomplete = GameState(cascades=(tuple(),) * 8, foundations=(13, 13, 13, 12)).to_packed()
        complete = GameState(cascades=(tuple(),) * 8, foundations=(13, 13, 13, 13)).to_packed()

        self.assertFalse(incomplete.is_victory)
        self.assertTrue(complete.is_victory)

    def test_packed_state_bitwise_count_helpers(self) -> None:
        all_empty = GameState(cascades=(tuple(),) * 8, freecells=(None, None, None, None), foundations=(0, 0, 0, 0)).to_packed()
        self.assertEqual(all_empty.freecell_count_empty(), 4)
        self.assertEqual(all_empty.cascade_count_empty(), 8)
        self.assertEqual(all_empty.cards_remaining(), 52)

        all_full = GameState(
            cascades=((c("AC"),), (c("2D"),), (c("3H"),), (c("4S"),), (c("5C"),), (c("6D"),), (c("7H"),), (c("8S"),)),
            freecells=(c("9C"), c("10D"), c("JH"), c("QS")),
            foundations=(13, 13, 13, 13),
        ).to_packed()
        self.assertEqual(all_full.freecell_count_empty(), 0)
        self.assertEqual(all_full.cascade_count_empty(), 0)
        self.assertEqual(all_full.cards_remaining(), 0)

        mixed = GameState(
            cascades=((c("AC"),), tuple(), (c("2H"), c("AS")), tuple(), tuple(), (c("KD"),), tuple(), (c("3C"),)),
            freecells=(None, c("4S"), None, c("5D")),
            foundations=(1, 3, 2, 0),
        ).to_packed()
        self.assertEqual(mixed.freecell_count_empty(), 2)
        self.assertEqual(mixed.cascade_count_empty(), 4)
        self.assertEqual(mixed.cards_remaining(), 46)


if __name__ == "__main__":
    unittest.main()
