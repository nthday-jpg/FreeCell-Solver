from .card import Card, SUITS, standard_deck
from .deal_generator import deal_cascades, microsoft_shuffled_deck, shuffled_deck
from .rules import (
	can_move_to_foundation,
	can_stack_on_cascade,
	is_descending_alternating,
	max_movable_cards,
)
from .state import GameState, Move, PileType
from .victory import cards_in_foundation, cards_remaining, is_victory, progress_ratio

__all__ = [
	"Card",
	"SUITS",
	"standard_deck",
	"shuffled_deck",
	"microsoft_shuffled_deck",
	"deal_cascades",
	"can_stack_on_cascade",
	"can_move_to_foundation",
	"is_descending_alternating",
	"max_movable_cards",
	"GameState",
	"Move",
	"PileType",
	"is_victory",
	"cards_in_foundation",
	"cards_remaining",
	"progress_ratio",
]
