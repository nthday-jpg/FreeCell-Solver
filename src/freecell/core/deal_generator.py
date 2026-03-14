from random import Random
from typing import Sequence

from .card import Card, standard_deck


_MS_RAND_MULTIPLIER = 214013
_MS_RAND_INCREMENT = 2531011
_MS_RAND_MASK = 0x7FFFFFFF


def _microsoft_rand_stream(seed: int) -> tuple[int, ...]:
	"""Return 52 outputs from the Microsoft C runtime rand() sequence."""
	state = seed & _MS_RAND_MASK
	values: list[int] = []
	for _ in range(52):
		state = (_MS_RAND_MULTIPLIER * state + _MS_RAND_INCREMENT) & _MS_RAND_MASK
		values.append((state >> 16) & 0x7FFF)
	return tuple(values)


def microsoft_shuffled_deck(deal_number: int) -> tuple[Card, ...]:
	"""Shuffle using the classic Microsoft FreeCell deal algorithm."""
	if deal_number < 0:
		raise ValueError("deal_number must be non-negative")

	deck = list(standard_deck())
	for idx, rand_value in zip(range(len(deck) - 1, -1, -1), _microsoft_rand_stream(deal_number)):
		swap_idx = rand_value % (idx + 1)
		deck[idx], deck[swap_idx] = deck[swap_idx], deck[idx]
	return tuple(deck)


def shuffled_deck(seed: int | None = None) -> tuple[Card, ...]:
	if seed is None:
		deck = list(standard_deck())
		Random(seed).shuffle(deck)
		return tuple(deck)
	return microsoft_shuffled_deck(seed)


def deal_cascades(
	seed: int | None = None,
	deck: Sequence[Card] | None = None,
	num_cascades: int = 8,
) -> tuple[tuple[Card, ...], ...]:
	if num_cascades <= 0:
		raise ValueError("num_cascades must be positive")

	cards = tuple(deck) if deck is not None else shuffled_deck(seed=seed)
	if len(cards) != 52:
		raise ValueError(f"FreeCell requires 52 cards, got {len(cards)}")

	cascades: list[list[Card]] = [[] for _ in range(num_cascades)]
	for idx, card in enumerate(cards):
		cascades[idx % num_cascades].append(card)
	return tuple(tuple(cascade) for cascade in cascades)
