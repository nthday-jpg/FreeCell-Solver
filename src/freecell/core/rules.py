from .card import Card


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


def max_movable_cards(empty_freecells: int, empty_cascades: int) -> int:
	if empty_freecells < 0 or empty_cascades < 0:
		raise ValueError("Counts must be non-negative")
	return (empty_freecells + 1) * (2 ** empty_cascades)
