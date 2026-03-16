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
from freecell.core.packed_state import PackedState
from freecell.core.state import GameState, Move


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

    def test_move_cascade_to_freecell_success_and_errors(self) -> None:
        state = GameState(
            cascades=((c("7C"), c("6D")), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
        )
        moved = state.move_cascade_to_freecell(cascade_index=0, freecell_index=1)

        self.assertEqual(moved.cascades[0], (c("7C"),))
        self.assertEqual(moved.freecells[1], c("6D"))
        self.assertEqual(state.cascades[0], (c("7C"), c("6D")))

        with self.assertRaisesRegex(ValueError, "Source cascade is empty"):
            state.move_cascade_to_freecell(cascade_index=1, freecell_index=0)

        occupied = GameState(cascades=((c("7C"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()), freecells=(c("AS"), None, None, None))
        with self.assertRaisesRegex(ValueError, "occupied"):
            occupied.move_cascade_to_freecell(cascade_index=0, freecell_index=0)

    def test_move_freecell_to_cascade_success_and_errors(self) -> None:
        state = GameState(
            cascades=((c("8C"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(c("7D"), None, None, None),
        )
        moved = state.move_freecell_to_cascade(freecell_index=0, cascade_index=0)

        self.assertEqual(moved.cascades[0], (c("8C"), c("7D")))
        self.assertIsNone(moved.freecells[0])

        with self.assertRaisesRegex(ValueError, "Source freecell is empty"):
            state.move_freecell_to_cascade(freecell_index=1, cascade_index=0)

        illegal = GameState(
            cascades=((c("8H"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(c("7D"), None, None, None),
        )
        with self.assertRaisesRegex(ValueError, "Illegal placement"):
            illegal.move_freecell_to_cascade(freecell_index=0, cascade_index=0)

    def test_move_cascade_to_foundation_success_and_errors(self) -> None:
        state = GameState(
            cascades=((c("AH"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            foundations=(0, 0, 0, 0),
        )
        moved = state.move_cascade_to_foundation(cascade_index=0)

        self.assertEqual(moved.cascades[0], tuple())
        self.assertEqual(moved.foundations, (0, 0, 1, 0))

        with self.assertRaisesRegex(ValueError, "Source cascade is empty"):
            state.move_cascade_to_foundation(cascade_index=1)

        blocked = GameState(
            cascades=((c("3H"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            foundations=(0, 0, 1, 0),
        )
        with self.assertRaisesRegex(ValueError, "cannot be moved"):
            blocked.move_cascade_to_foundation(cascade_index=0)

    def test_move_freecell_to_foundation_success_and_errors(self) -> None:
        state = GameState(
            cascades=(tuple(),) * 8,
            freecells=(c("AD"), None, None, None),
            foundations=(0, 0, 0, 0),
        )
        moved = state.move_freecell_to_foundation(freecell_index=0)

        self.assertEqual(moved.freecells, (None, None, None, None))
        self.assertEqual(moved.foundations, (0, 1, 0, 0))

        with self.assertRaisesRegex(ValueError, "Source freecell is empty"):
            state.move_freecell_to_foundation(freecell_index=1)

        blocked = GameState(
            cascades=(tuple(),) * 8,
            freecells=(c("4D"), None, None, None),
            foundations=(0, 1, 0, 0),
        )
        with self.assertRaisesRegex(ValueError, "cannot be moved"):
            blocked.move_freecell_to_foundation(freecell_index=0)

    def test_move_cascade_to_cascade_success_multi_card(self) -> None:
        state = GameState(
            cascades=((c("8C"), c("7D"), c("6C")), (c("9H"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
        )
        moved = state.move_cascade_to_cascade(source_index=0, destination_index=1, count=3)

        self.assertEqual(moved.cascades[0], tuple())
        self.assertEqual(moved.cascades[1], (c("9H"), c("8C"), c("7D"), c("6C")))

    def test_move_cascade_to_cascade_validates_constraints(self) -> None:
        base = GameState(
            cascades=((c("8C"), c("7D")), (c("9H"),), (c("AS"),), (c("2D"),), (c("3S"),), (c("4D"),), (c("5S"),), (c("6D"),)),
            freecells=(c("KH"), c("KC"), c("QH"), c("QC")),
        )

        with self.assertRaisesRegex(ValueError, "count must be positive"):
            base.move_cascade_to_cascade(source_index=0, destination_index=1, count=0)

        with self.assertRaisesRegex(ValueError, "must differ"):
            base.move_cascade_to_cascade(source_index=0, destination_index=0, count=1)

        with self.assertRaisesRegex(ValueError, "does not contain enough cards"):
            base.move_cascade_to_cascade(source_index=0, destination_index=1, count=3)

        bad_stack = GameState(
            cascades=((c("8C"), c("6D")), (c("9H"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
        )
        with self.assertRaisesRegex(ValueError, "not in descending alternating"):
            bad_stack.move_cascade_to_cascade(source_index=0, destination_index=1, count=2)

        with self.assertRaisesRegex(ValueError, "current free space"):
            base.move_cascade_to_cascade(source_index=0, destination_index=1, count=2)

        illegal_destination = GameState(
            cascades=((c("8C"), c("7D")), (c("8H"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
        )
        with self.assertRaisesRegex(ValueError, "Illegal placement"):
            illegal_destination.move_cascade_to_cascade(source_index=0, destination_index=1, count=1)

    def test_apply_move_dispatch_and_validation(self) -> None:
        state = GameState(
            cascades=((c("8C"), c("7D")), (c("9H"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
        )

        moved = state.apply_move(Move(source="cascade", source_index=0, destination="freecell", destination_index=0))
        self.assertEqual(moved.freecells[0], c("7D"))

        with self.assertRaisesRegex(ValueError, "Only one card"):
            state.apply_move(Move(source="cascade", source_index=0, destination="freecell", destination_index=0, count=2))

        with self.assertRaisesRegex(ValueError, "Unsupported move"):
            state.apply_move(Move(source="foundation", source_index=0, destination="cascade", destination_index=0))

    def test_packed_state_move_methods_match_game_state(self) -> None:
        # Cascade -> freecell
        state = GameState(
            cascades=((c("8C"), c("7D"), c("6C")), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
            foundations=(0, 0, 0, 0),
        )
        packed = PackedState.from_game_state(state)
        self.assertEqual(packed.move_cascade_to_freecell(0, 1).to_game_state(), state.move_cascade_to_freecell(0, 1))

        # Freecell -> cascade (legal: 7D onto 8C)
        state = GameState(
            cascades=((c("8C"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(c("7D"), None, None, None),
            foundations=(0, 0, 0, 0),
        )
        packed = PackedState.from_game_state(state)
        self.assertEqual(packed.move_freecell_to_cascade(0, 0).to_game_state(), state.move_freecell_to_cascade(0, 0))

        # Cascade -> foundation
        state = GameState(
            cascades=((c("AH"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
            foundations=(0, 0, 0, 0),
        )
        packed = PackedState.from_game_state(state)
        self.assertEqual(packed.move_cascade_to_foundation(0).to_game_state(), state.move_cascade_to_foundation(0))

        # Freecell -> foundation
        state = GameState(
            cascades=(tuple(),) * 8,
            freecells=(c("AD"), None, None, None),
            foundations=(0, 0, 0, 0),
        )
        packed = PackedState.from_game_state(state)
        self.assertEqual(packed.move_freecell_to_foundation(0).to_game_state(), state.move_freecell_to_foundation(0))

        # Multi-card cascade -> cascade
        state = GameState(
            cascades=((c("8C"), c("7D"), c("6C")), (c("9H"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
            foundations=(0, 0, 0, 0),
        )
        packed = PackedState.from_game_state(state)
        self.assertEqual(packed.move_cascade_to_cascade(0, 1, count=3).to_game_state(), state.move_cascade_to_cascade(0, 1, count=3))

    def test_packed_state_apply_move_dispatch_and_validation(self) -> None:
        state = GameState(
            cascades=((c("8C"), c("7D")), (c("9H"),), tuple(), tuple(), tuple(), tuple(), tuple(), tuple()),
            freecells=(None, None, None, None),
        )
        packed = state.to_packed()

        moved = packed.apply_move(Move(source="cascade", source_index=0, destination="freecell", destination_index=0))
        self.assertEqual(moved.to_game_state(), state.apply_move(Move(source="cascade", source_index=0, destination="freecell", destination_index=0)))

        with self.assertRaisesRegex(ValueError, "Only one card"):
            packed.apply_move(Move(source="cascade", source_index=0, destination="freecell", destination_index=0, count=2))

        with self.assertRaisesRegex(ValueError, "Unsupported move"):
            packed.apply_move(Move(source="foundation", source_index=0, destination="cascade", destination_index=0))

    def test_packed_state_victory_helpers(self) -> None:
        incomplete = GameState(cascades=(tuple(),) * 8, foundations=(13, 13, 13, 12)).to_packed()
        complete = GameState(cascades=(tuple(),) * 8, foundations=(13, 13, 13, 13)).to_packed()

        self.assertFalse(incomplete.is_victory)
        self.assertTrue(complete.is_victory)


if __name__ == "__main__":
    unittest.main()
