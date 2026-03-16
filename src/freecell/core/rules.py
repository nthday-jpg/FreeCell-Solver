from .card import Card
from .card import CARD_CODE_IS_RED, CARD_CODE_RANK


def is_descending_alternating(cards: tuple[Card, ...]) -> bool:
	if len(cards) <= 1:
		return True
	for lower, upper in zip(cards, cards[1:]):
		if lower.rank != upper.rank + 1:
			return False
		if lower.color == upper.color:
			return False
	return True


def can_stack_on_cascade(moving: Card, destination_top: Card | None) -> bool:
	if destination_top is None:
		return True
	if moving.color == destination_top.color:
		return False
	return moving.rank + 1 == destination_top.rank


def can_move_to_foundation(card: Card, current_rank: int) -> bool:
	return card.rank == current_rank + 1


def is_descending_alternating_codes(card_codes: tuple[int, ...]) -> bool:
	if len(card_codes) <= 1:
		return True
	for lower_code, upper_code in zip(card_codes, card_codes[1:]):
		if CARD_CODE_RANK[lower_code] != CARD_CODE_RANK[upper_code] + 1:
			return False
		if CARD_CODE_IS_RED[lower_code] == CARD_CODE_IS_RED[upper_code]:
			return False
	return True


def can_stack_on_cascade_code(moving_code: int, destination_top_code: int | None) -> bool:
	if destination_top_code is None:
		return True
	if CARD_CODE_IS_RED[moving_code] == CARD_CODE_IS_RED[destination_top_code]:
		return False
	return CARD_CODE_RANK[moving_code] + 1 == CARD_CODE_RANK[destination_top_code]


def can_move_to_foundation_code(card_code: int, current_rank: int) -> bool:
	return CARD_CODE_RANK[card_code] == current_rank + 1


def max_movable_cards(empty_freecells: int, empty_cascades: int) -> int:
	if empty_freecells < 0 or empty_cascades < 0:
		raise ValueError("Counts must be non-negative")
	return (empty_freecells + 1) * (2 ** empty_cascades)
