from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .card import (
    Card,
    EMPTY_CARD_CODE,
    card_code_suit_index,
    card_to_code,
    code_to_card,
)
from .rules import (
    can_move_to_foundation_code,
    can_stack_on_cascade_code,
    is_descending_alternating_codes,
    max_movable_cards,
)

if TYPE_CHECKING:
    from .state import GameState
    from .state import Move

_CARD_BITS = 6
_CARD_MASK = (1 << _CARD_BITS) - 1
_CASCADE_COUNT = 8
_FREECELL_COUNT = 4
_FOUNDATION_COUNT = 4
_FOUNDATION_BITS = 4
_CASCADE_LEN_BITS = 4
_MAX_FOUNDATION_RANK = 13
_FOUNDATION_COMPLETE_MASK = sum(
    _MAX_FOUNDATION_RANK << (i * _FOUNDATION_BITS)
    for i in range(_FOUNDATION_COUNT)
)


def _slot_mask(bit_width: int, index: int) -> int:
    return ((1 << bit_width) - 1) << (index * bit_width)


@dataclass(frozen=True, slots=True)
class PackedState:
    """
        cascade_words:
            Tuple of 8 integer, one per cascade
            Each integer store all cards, packed in 6bit chunk
        cascade_lengths: 
            stores 8 cascade lengths, each in 4bits
        freecells: 
            4 freecell slots, each in 6 bits
            EMPTY_CARD_CODE(63) as sentinel for empty
        foundations:
            4 foundation ranks, each in 4 bits
    """

    cascade_words: tuple[int, ...]
    cascade_lengths: int
    freecells: int
    foundations: int

    @property
    def is_victory(self) -> bool:
        return self.foundations == _FOUNDATION_COMPLETE_MASK

    @property
    def cascade_count(self) -> int:
        return _CASCADE_COUNT

    @property
    def freecell_slot_count(self) -> int:
        return _FREECELL_COUNT
    
    @classmethod
    def from_game_state(cls, state: "GameState") -> "PackedState":
        if len(state.cascades) != _CASCADE_COUNT:
            raise ValueError(f"Expected {_CASCADE_COUNT} cascades, got {len(state.cascades)}")
        if len(state.freecells) != _FREECELL_COUNT:
            raise ValueError(f"Expected {_FREECELL_COUNT} freecells, got {len(state.freecells)}")
        if len(state.foundations) != _FOUNDATION_COUNT:
            raise ValueError(f"Expected {_FOUNDATION_COUNT} foundations, got {len(state.foundations)}")

        cascade_words: list[int] = [0] * _CASCADE_COUNT
        cascade_lengths = 0
        for index, cascade in enumerate(state.cascades):
            if len(cascade) > 13:
                raise ValueError("Cascade cannot exceed 13 cards")
            word = 0
            for position, card in enumerate(cascade):
                word |= card_to_code(card) << (position * _CARD_BITS)
            cascade_words[index] = word
            cascade_lengths |= len(cascade) << (index * _CASCADE_LEN_BITS)

        freecells = 0
        for index, card in enumerate(state.freecells):
            code = EMPTY_CARD_CODE if card is None else card_to_code(card)
            freecells |= code << (index * _CARD_BITS)

        foundations = 0
        for index, rank in enumerate(state.foundations):
            if rank < 0 or rank > 13:
                raise ValueError(f"Foundation rank must be between 0 and 13, got {rank}")
            foundations |= rank << (index * _FOUNDATION_BITS)

        return cls(
            cascade_words=tuple(cascade_words),
            cascade_lengths=cascade_lengths,
            freecells=freecells,
            foundations=foundations,
        )

    def to_game_state(self) -> "GameState":
        if len(self.cascade_words) != _CASCADE_COUNT:
            raise ValueError(f"Expected {_CASCADE_COUNT} packed cascade words, got {len(self.cascade_words)}")

        cascades: list[tuple[Card, ...]] = []
        for index in range(_CASCADE_COUNT):
            length = self.cascade_length(index)
            cards = tuple(
                code_to_card((self.cascade_words[index] >> (position * _CARD_BITS)) & _CARD_MASK)
                for position in range(length)
            )
            cascades.append(cards)

        freecells = tuple(
            None if code == EMPTY_CARD_CODE else code_to_card(code)
            for code in (self.freecell(index) for index in range(_FREECELL_COUNT))
        )

        foundations = (
            self.foundation_rank(0),
            self.foundation_rank(1),
            self.foundation_rank(2),
            self.foundation_rank(3),
        )

        from .state import GameState

        return GameState(
            cascades=tuple(cascades),
            freecells=freecells,
            foundations=foundations,
        )

    def key(self) -> tuple[int, ...]:
        return (*self.cascade_words, self.cascade_lengths, self.freecells, self.foundations)

    def cascade_length(self, index: int) -> int:
        return (self.cascade_lengths >> (index * _CASCADE_LEN_BITS)) & 0xF

    def freecell(self, index: int) -> int:
        return (self.freecells >> (index * _CARD_BITS)) & _CARD_MASK

    def freecell_count_empty(self) -> int:
        return sum(1 for index in range(_FREECELL_COUNT) if self.freecell(index) == EMPTY_CARD_CODE)

    def foundation_rank(self, suit_index: int) -> int:
        return (self.foundations >> (suit_index * _FOUNDATION_BITS)) & 0xF

    def cascade_top(self, index: int) -> int | None:
        length = self.cascade_length(index)
        if length == 0:
            return None
        return (self.cascade_words[index] >> ((length - 1) * _CARD_BITS)) & _CARD_MASK

    def cascade_card_code(self, cascade_index: int, position: int) -> int:
        length = self.cascade_length(cascade_index)
        if position < 0 or position >= length:
            raise ValueError(f"Position {position} out of bounds for cascade length {length}")
        return (self.cascade_words[cascade_index] >> (position * _CARD_BITS)) & _CARD_MASK

    def cascade_tail_codes(self, cascade_index: int, count: int) -> tuple[int, ...]:
        length = self.cascade_length(cascade_index)
        if count <= 0:
            raise ValueError("count must be positive")
        if count > length:
            raise ValueError("count exceeds cascade length")
        start = length - count
        return tuple(self.cascade_card_code(cascade_index, position) for position in range(start, length))

    def cascade_count_empty(self) -> int:
        return sum(1 for index in range(_CASCADE_COUNT) if self.cascade_length(index) == 0)

    def move_cascade_to_freecell(self, cascade_index: int, freecell_index: int) -> "PackedState":
        source_len = self.cascade_length(cascade_index)
        if source_len == 0:
            raise ValueError("Source cascade is empty")
        if self.freecell(freecell_index) != EMPTY_CARD_CODE:
            raise ValueError("Destination freecell is occupied")

        source_word = self.cascade_words[cascade_index]
        top_shift = (source_len - 1) * _CARD_BITS
        moving = (source_word >> top_shift) & _CARD_MASK

        source_new_len = source_len - 1
        source_keep_mask = (1 << (source_new_len * _CARD_BITS)) - 1 if source_new_len > 0 else 0
        source_new_word = source_word & source_keep_mask

        new_words = list(self.cascade_words)
        new_words[cascade_index] = source_new_word

        new_lengths = (
            self.cascade_lengths
            & ~_slot_mask(_CASCADE_LEN_BITS, cascade_index)
            | (source_new_len << (cascade_index * _CASCADE_LEN_BITS))
        )

        new_freecells = (
            self.freecells
            & ~_slot_mask(_CARD_BITS, freecell_index)
            | (moving << (freecell_index * _CARD_BITS))
        )

        return PackedState(
            cascade_words=tuple(new_words),
            cascade_lengths=new_lengths,
            freecells=new_freecells,
            foundations=self.foundations,
        )

    def move_freecell_to_cascade(self, freecell_index: int, cascade_index: int) -> "PackedState":
        moving = self.freecell(freecell_index)
        if moving == EMPTY_CARD_CODE:
            raise ValueError("Source freecell is empty")

        dest_len = self.cascade_length(cascade_index)
        destination_top = self.cascade_top(cascade_index)
        if not can_stack_on_cascade_code(moving, destination_top):
            raise ValueError("Illegal placement on cascade")

        dest_new_len = dest_len + 1
        dest_new_word = self.cascade_words[cascade_index] | (moving << (dest_len * _CARD_BITS))

        new_words = list(self.cascade_words)
        new_words[cascade_index] = dest_new_word

        new_lengths = (
            self.cascade_lengths
            & ~_slot_mask(_CASCADE_LEN_BITS, cascade_index)
            | (dest_new_len << (cascade_index * _CASCADE_LEN_BITS))
        )

        new_freecells = self.freecells & ~_slot_mask(_CARD_BITS, freecell_index)
        new_freecells |= EMPTY_CARD_CODE << (freecell_index * _CARD_BITS)

        return PackedState(
            cascade_words=tuple(new_words),
            cascade_lengths=new_lengths,
            freecells=new_freecells,
            foundations=self.foundations,
        )

    def move_cascade_to_foundation(self, cascade_index: int) -> "PackedState":
        source_len = self.cascade_length(cascade_index)
        if source_len == 0:
            raise ValueError("Source cascade is empty")

        source_word = self.cascade_words[cascade_index]
        top_shift = (source_len - 1) * _CARD_BITS
        moving = (source_word >> top_shift) & _CARD_MASK
        suit_index = card_code_suit_index(moving)
        current_rank = self.foundation_rank(suit_index)
        if not can_move_to_foundation_code(moving, current_rank):
            raise ValueError("Card cannot be moved to foundation")

        source_new_len = source_len - 1
        source_keep_mask = (1 << (source_new_len * _CARD_BITS)) - 1 if source_new_len > 0 else 0
        source_new_word = source_word & source_keep_mask

        new_words = list(self.cascade_words)
        new_words[cascade_index] = source_new_word

        new_lengths = (
            self.cascade_lengths
            & ~_slot_mask(_CASCADE_LEN_BITS, cascade_index)
            | (source_new_len << (cascade_index * _CASCADE_LEN_BITS))
        )

        new_foundations = self.foundations & ~_slot_mask(_FOUNDATION_BITS, suit_index)
        new_foundations |= ((current_rank + 1) << (suit_index * _FOUNDATION_BITS))

        return PackedState(
            cascade_words=tuple(new_words),
            cascade_lengths=new_lengths,
            freecells=self.freecells,
            foundations=new_foundations,
        )

    def move_freecell_to_foundation(self, freecell_index: int) -> "PackedState":
        moving = self.freecell(freecell_index)
        if moving == EMPTY_CARD_CODE:
            raise ValueError("Source freecell is empty")

        suit_index = card_code_suit_index(moving)
        current_rank = self.foundation_rank(suit_index)
        if not can_move_to_foundation_code(moving, current_rank):
            raise ValueError("Card cannot be moved to foundation")

        new_freecells = self.freecells & ~_slot_mask(_CARD_BITS, freecell_index)
        new_freecells |= EMPTY_CARD_CODE << (freecell_index * _CARD_BITS)

        new_foundations = self.foundations & ~_slot_mask(_FOUNDATION_BITS, suit_index)
        new_foundations |= ((current_rank + 1) << (suit_index * _FOUNDATION_BITS))

        return PackedState(
            cascade_words=self.cascade_words,
            cascade_lengths=self.cascade_lengths,
            freecells=new_freecells,
            foundations=new_foundations,
        )

    def move_cascade_to_cascade(self, source_index: int, destination_index: int, count: int = 1) -> "PackedState":
        if count <= 0:
            raise ValueError("count must be positive")
        if source_index == destination_index:
            raise ValueError("Source and destination cascades must differ")

        source_len = self.cascade_length(source_index)
        destination_len = self.cascade_length(destination_index)
        if source_len < count:
            raise ValueError("Source cascade does not contain enough cards")

        source_word = self.cascade_words[source_index]
        moving_shift = (source_len - count) * _CARD_BITS
        moving_mask = (1 << (count * _CARD_BITS)) - 1
        moving_bits = (source_word >> moving_shift) & moving_mask
        moving_stack = tuple((moving_bits >> (i * _CARD_BITS)) & _CARD_MASK for i in range(count))
        if not is_descending_alternating_codes(moving_stack):
            raise ValueError("Moving stack is not in descending alternating order")

        destination_is_empty = destination_len == 0
        auxiliary_empty_cascades = self.cascade_count_empty() - (1 if destination_is_empty else 0)
        allowed = max_movable_cards(self.freecell_count_empty(), auxiliary_empty_cascades)
        if count > allowed:
            raise ValueError(f"Cannot move {count} cards with current free space (max {allowed})")

        destination_top = self.cascade_top(destination_index)
        if not can_stack_on_cascade_code(moving_stack[0], destination_top):
            raise ValueError("Illegal placement on destination cascade")

        source_new_len = source_len - count
        source_keep_mask = (1 << (source_new_len * _CARD_BITS)) - 1 if source_new_len > 0 else 0
        source_new_word = source_word & source_keep_mask
        destination_new_word = self.cascade_words[destination_index] | (moving_bits << (destination_len * _CARD_BITS))

        new_words = list(self.cascade_words)
        new_words[source_index] = source_new_word
        new_words[destination_index] = destination_new_word

        new_lengths = self.cascade_lengths
        new_lengths = new_lengths & ~_slot_mask(_CASCADE_LEN_BITS, source_index)
        new_lengths |= source_new_len << (source_index * _CASCADE_LEN_BITS)
        new_lengths = new_lengths & ~_slot_mask(_CASCADE_LEN_BITS, destination_index)
        new_lengths |= (destination_len + count) << (destination_index * _CASCADE_LEN_BITS)

        return PackedState(
            cascade_words=tuple(new_words),
            cascade_lengths=new_lengths,
            freecells=self.freecells,
            foundations=self.foundations,
        )

    def apply_move(self, move: "Move") -> "PackedState":
        if move.source == "cascade" and move.destination == "cascade":
            return self.move_cascade_to_cascade(move.source_index, move.destination_index, count=move.count)
        if move.source == "cascade" and move.destination == "freecell":
            if move.count != 1:
                raise ValueError("Only one card can be moved to freecell")
            return self.move_cascade_to_freecell(move.source_index, move.destination_index)
        if move.source == "freecell" and move.destination == "cascade":
            if move.count != 1:
                raise ValueError("Only one card can be moved from freecell")
            return self.move_freecell_to_cascade(move.source_index, move.destination_index)
        if move.source == "cascade" and move.destination == "foundation":
            if move.count != 1:
                raise ValueError("Only one card can be moved to foundation")
            return self.move_cascade_to_foundation(move.source_index)
        if move.source == "freecell" and move.destination == "foundation":
            if move.count != 1:
                raise ValueError("Only one card can be moved to foundation")
            return self.move_freecell_to_foundation(move.source_index)
        raise ValueError(f"Unsupported move: {move}")
