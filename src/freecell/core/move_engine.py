from __future__ import annotations

from typing import TYPE_CHECKING

from .card import EMPTY_CARD_CODE, card_code_suit_index
from .rules import (
	can_move_to_foundation_code,
	can_stack_on_cascade_code,
	is_descending_alternating_codes,
	max_movable_cards,
)

if TYPE_CHECKING:
	from .packed_state import PackedState
	from .state import Move

_CARD_BITS = 6
_CARD_MASK = (1 << _CARD_BITS) - 1
_CASCADE_LEN_BITS = 4
_FOUNDATION_BITS = 4


def _slot_mask(bit_width: int, index: int) -> int:
	return ((1 << bit_width) - 1) << (index * bit_width)

_SLOT_MASKS_CASCADE_LEN = tuple(_slot_mask(_CASCADE_LEN_BITS, i) for i in range(8))
_SLOT_MASKS_CARD = tuple(_slot_mask(_CARD_BITS, i) for i in range(8))
_SLOT_MASKS_FOUNDATION = tuple(_slot_mask(_FOUNDATION_BITS, i) for i in range(4))


def _new_state(state: "PackedState", *, cascade_words: tuple[int, ...], cascade_lengths: int, freecells: int, foundations: int) -> "PackedState":
	return state.__class__(
		cascade_words=cascade_words,
		cascade_lengths=cascade_lengths,
		freecells=freecells,
		foundations=foundations,
	)


def move_packed_cascade_to_freecell(
	state: "PackedState",
	cascade_index: int,
	freecell_index: int,
	*,
	validate: bool = True,
) -> "PackedState":
	source_len = state.cascade_length(cascade_index)
	if validate and source_len == 0:
		raise ValueError("Source cascade is empty")
	if validate and state.freecell(freecell_index) != EMPTY_CARD_CODE:
		raise ValueError("Destination freecell is occupied")

	source_word = state.cascade_words[cascade_index]
	top_shift = (source_len - 1) * _CARD_BITS
	moving = (source_word >> top_shift) & _CARD_MASK

	source_new_len = source_len - 1
	source_keep_mask = (1 << (source_new_len * _CARD_BITS)) - 1 if source_new_len > 0 else 0
	source_new_word = source_word & source_keep_mask

	new_words = list(state.cascade_words)
	new_words[cascade_index] = source_new_word

	new_lengths = (
		state.cascade_lengths
		& ~_SLOT_MASKS_CASCADE_LEN[cascade_index]
		| (source_new_len << (cascade_index * _CASCADE_LEN_BITS))
	)

	new_freecells = (
		state.freecells
		& ~_SLOT_MASKS_CARD[freecell_index]
		| (moving << (freecell_index * _CARD_BITS))
	)

	return _new_state(
		state,
		cascade_words=tuple(new_words),
		cascade_lengths=new_lengths,
		freecells=new_freecells,
		foundations=state.foundations,
	)


def move_packed_freecell_to_cascade(
	state: "PackedState",
	freecell_index: int,
	cascade_index: int,
	*,
	validate: bool = True,
) -> "PackedState":
	moving = state.freecell(freecell_index)
	if validate and moving == EMPTY_CARD_CODE:
		raise ValueError("Source freecell is empty")

	dest_len = state.cascade_length(cascade_index)
	destination_top = state.cascade_top(cascade_index)
	if validate and not can_stack_on_cascade_code(moving, destination_top):
		raise ValueError("Illegal placement on cascade")

	dest_new_len = dest_len + 1
	dest_new_word = state.cascade_words[cascade_index] | (moving << (dest_len * _CARD_BITS))

	new_words = list(state.cascade_words)
	new_words[cascade_index] = dest_new_word

	new_lengths = (
		state.cascade_lengths
		& ~_SLOT_MASKS_CASCADE_LEN[cascade_index]
		| (dest_new_len << (cascade_index * _CASCADE_LEN_BITS))
	)

	new_freecells = state.freecells & ~_SLOT_MASKS_CARD[freecell_index]
	new_freecells |= EMPTY_CARD_CODE << (freecell_index * _CARD_BITS)

	return _new_state(
		state,
		cascade_words=tuple(new_words),
		cascade_lengths=new_lengths,
		freecells=new_freecells,
		foundations=state.foundations,
	)


def move_packed_cascade_to_foundation(
	state: "PackedState",
	cascade_index: int,
	*,
	validate: bool = True,
) -> "PackedState":
	source_len = state.cascade_length(cascade_index)
	if validate and source_len == 0:
		raise ValueError("Source cascade is empty")

	source_word = state.cascade_words[cascade_index]
	top_shift = (source_len - 1) * _CARD_BITS
	moving = (source_word >> top_shift) & _CARD_MASK
	suit_index = card_code_suit_index(moving)
	current_rank = state.foundation_rank(suit_index)
	if validate and not can_move_to_foundation_code(moving, current_rank):
		raise ValueError("Card cannot be moved to foundation")

	source_new_len = source_len - 1
	source_keep_mask = (1 << (source_new_len * _CARD_BITS)) - 1 if source_new_len > 0 else 0
	source_new_word = source_word & source_keep_mask

	new_words = list(state.cascade_words)
	new_words[cascade_index] = source_new_word

	new_lengths = (
		state.cascade_lengths
		& ~_SLOT_MASKS_CASCADE_LEN[cascade_index]
		| (source_new_len << (cascade_index * _CASCADE_LEN_BITS))
	)

	new_foundations = state.foundations & ~_SLOT_MASKS_FOUNDATION[suit_index]
	new_foundations |= ((current_rank + 1) << (suit_index * _FOUNDATION_BITS))

	return _new_state(
		state,
		cascade_words=tuple(new_words),
		cascade_lengths=new_lengths,
		freecells=state.freecells,
		foundations=new_foundations,
	)


def move_packed_freecell_to_foundation(
	state: "PackedState",
	freecell_index: int,
	*,
	validate: bool = True,
) -> "PackedState":
	moving = state.freecell(freecell_index)
	if validate and moving == EMPTY_CARD_CODE:
		raise ValueError("Source freecell is empty")

	suit_index = card_code_suit_index(moving)
	current_rank = state.foundation_rank(suit_index)
	if validate and not can_move_to_foundation_code(moving, current_rank):
		raise ValueError("Card cannot be moved to foundation")

	new_freecells = state.freecells & ~_SLOT_MASKS_CARD[freecell_index]
	new_freecells |= EMPTY_CARD_CODE << (freecell_index * _CARD_BITS)

	new_foundations = state.foundations & ~_SLOT_MASKS_FOUNDATION[suit_index]
	new_foundations |= ((current_rank + 1) << (suit_index * _FOUNDATION_BITS))

	return _new_state(
		state,
		cascade_words=state.cascade_words,
		cascade_lengths=state.cascade_lengths,
		freecells=new_freecells,
		foundations=new_foundations,
	)


def move_packed_cascade_to_cascade(
		state: "PackedState", 
		source_index: int, 
		destination_index: int, 
		count: int = 1,
		*,
		validate: bool = True
	) -> "PackedState":

	if count <= 0:
		raise ValueError("count must be positive")
	if source_index == destination_index:
		raise ValueError("Source and destination cascades must differ")

	source_len = state.cascade_length(source_index)
	destination_len = state.cascade_length(destination_index)
	if source_len < count:
		raise ValueError("Source cascade does not contain enough cards")

	source_word = state.cascade_words[source_index]
	moving_shift = (source_len - count) * _CARD_BITS
	moving_mask = (1 << (count * _CARD_BITS)) - 1
	moving_bits = (source_word >> moving_shift) & moving_mask

	if validate:
		moving_stack = tuple((moving_bits >> (i * _CARD_BITS)) & _CARD_MASK for i in range(count))
		if not is_descending_alternating_codes(moving_stack):
			raise ValueError("Moving stack is not in descending alternating order")

		destination_is_empty = destination_len == 0
		auxiliary_empty_cascades = state.cascade_count_empty() - (1 if destination_is_empty else 0)
		allowed = max_movable_cards(state.freecell_count_empty(), auxiliary_empty_cascades)
		if count > allowed:
			raise ValueError(f"Cannot move {count} cards with current free space (max {allowed})")

		destination_top = state.cascade_top(destination_index)
		if not can_stack_on_cascade_code(moving_stack[0], destination_top):
			raise ValueError("Illegal placement on destination cascade")

	source_new_len = source_len - count
	source_keep_mask = (1 << (source_new_len * _CARD_BITS)) - 1 if source_new_len > 0 else 0
	source_new_word = source_word & source_keep_mask
	destination_new_word = state.cascade_words[destination_index] | (moving_bits << (destination_len * _CARD_BITS))

	new_words = list(state.cascade_words)
	new_words[source_index] = source_new_word
	new_words[destination_index] = destination_new_word

	new_lengths = state.cascade_lengths
	new_lengths = new_lengths & ~_SLOT_MASKS_CASCADE_LEN[source_index]
	new_lengths |= source_new_len << (source_index * _CASCADE_LEN_BITS)
	new_lengths = new_lengths & ~_SLOT_MASKS_CASCADE_LEN[destination_index]
	new_lengths |= (destination_len + count) << (destination_index * _CASCADE_LEN_BITS)

	return _new_state(
		state,
		cascade_words=tuple(new_words),
		cascade_lengths=new_lengths,
		freecells=state.freecells,
		foundations=state.foundations,
	)


def apply_packed_move(state: "PackedState", move: "Move", *, validate: bool = True) -> "PackedState":
	if move.source == "cascade" and move.destination == "cascade":
		return move_packed_cascade_to_cascade(
			state,
			move.source_index,
			move.destination_index,
			count=move.count,
			validate=validate,
		)
	if move.source == "cascade" and move.destination == "freecell":
		if validate and move.count != 1:
			raise ValueError("Only one card can be moved to freecell")
		return move_packed_cascade_to_freecell(
			state,
			move.source_index,
			move.destination_index,
			validate=validate,
		)
	if move.source == "freecell" and move.destination == "cascade":
		if validate and move.count != 1:
			raise ValueError("Only one card can be moved from freecell")
		return move_packed_freecell_to_cascade(
			state,
			move.source_index,
			move.destination_index,
			validate=validate,
		)
	if move.source == "cascade" and move.destination == "foundation":
		if validate and move.count != 1:
			raise ValueError("Only one card can be moved to foundation")
		return move_packed_cascade_to_foundation(
			state,
			move.source_index,
			validate=validate,
		)
	if move.source == "freecell" and move.destination == "foundation":
		if validate and move.count != 1:
			raise ValueError("Only one card can be moved to foundation")
		return move_packed_freecell_to_foundation(
			state,
			move.source_index,
			validate=validate,
		)
	raise ValueError(f"Unsupported move: {move}")
