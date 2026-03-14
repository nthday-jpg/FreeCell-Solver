from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core.card import Card
from freecell.core.rules import (
    can_move_to_foundation,
    can_stack_on_cascade,
    is_descending_alternating,
    max_movable_cards,
)


class RulesTests(unittest.TestCase):
    def test_is_descending_alternating_accepts_empty_and_single(self) -> None:
        self.assertTrue(is_descending_alternating(tuple()))
        self.assertTrue(is_descending_alternating((Card.from_short_name("KD"),)))

    def test_is_descending_alternating_accepts_valid_sequence(self) -> None:
        stack = (
            Card.from_short_name("KC"),
            Card.from_short_name("QH"),
            Card.from_short_name("JS"),
            Card.from_short_name("10D"),
        )
        self.assertTrue(is_descending_alternating(stack))

    def test_is_descending_alternating_rejects_invalid_rank_step(self) -> None:
        stack = (Card.from_short_name("KC"), Card.from_short_name("JH"))
        self.assertFalse(is_descending_alternating(stack))

    def test_is_descending_alternating_rejects_same_color_neighbors(self) -> None:
        stack = (Card.from_short_name("KC"), Card.from_short_name("QS"))
        self.assertFalse(is_descending_alternating(stack))

    def test_can_stack_on_cascade_accepts_empty_destination(self) -> None:
        self.assertTrue(can_stack_on_cascade(Card.from_short_name("7D"), None))

    def test_can_stack_on_cascade_rejects_same_color(self) -> None:
        moving = Card.from_short_name("7D")
        destination_top = Card.from_short_name("8H")
        self.assertFalse(can_stack_on_cascade(moving, destination_top))

    def test_can_stack_on_cascade_rejects_wrong_rank_relation(self) -> None:
        moving = Card.from_short_name("7D")
        destination_top = Card.from_short_name("9C")
        self.assertFalse(can_stack_on_cascade(moving, destination_top))

    def test_can_stack_on_cascade_accepts_opposite_color_and_one_rank_lower(self) -> None:
        moving = Card.from_short_name("7D")
        destination_top = Card.from_short_name("8C")
        self.assertTrue(can_stack_on_cascade(moving, destination_top))

    def test_can_move_to_foundation(self) -> None:
        self.assertTrue(can_move_to_foundation(Card.from_short_name("AD"), current_rank=0))
        self.assertTrue(can_move_to_foundation(Card.from_short_name("7D"), current_rank=6))
        self.assertFalse(can_move_to_foundation(Card.from_short_name("7D"), current_rank=5))

    def test_max_movable_cards(self) -> None:
        self.assertEqual(max_movable_cards(empty_freecells=0, empty_cascades=0), 1)
        self.assertEqual(max_movable_cards(empty_freecells=2, empty_cascades=1), 6)
        self.assertEqual(max_movable_cards(empty_freecells=4, empty_cascades=3), 40)

    def test_max_movable_cards_rejects_negative_counts(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            max_movable_cards(empty_freecells=-1, empty_cascades=0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            max_movable_cards(empty_freecells=0, empty_cascades=-1)


if __name__ == "__main__":
    unittest.main()
