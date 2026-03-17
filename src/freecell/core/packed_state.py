from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .card import (
    Card,
    EMPTY_CARD_CODE,
    card_to_code,
    code_to_card,
)
from .move_engine import (
    apply_packed_move,
    move_packed_cascade_to_cascade,
    move_packed_cascade_to_foundation,
    move_packed_cascade_to_freecell,
    move_packed_freecell_to_cascade,
    move_packed_freecell_to_foundation,
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
        # count = 0
        # for i in range(_FREECELL_COUNT):
        #     if self.freecell(i) == EMPTY_CARD_CODE:
        #         count+=1
        # return count

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
        # Extract tail as one bit window, then decode each card code in order.
        tail_bits = self.cascade_words[cascade_index] >> (start * _CARD_BITS)
        return tuple((tail_bits >> (offset * _CARD_BITS)) & _CARD_MASK for offset in range(count))

    def cascade_count_empty(self) -> int:
        # count = 0
        # for i in range(_CASCADE_COUNT):
        #     if ((self.cascade_lengths >> (i * _CASCADE_LEN_BITS)) & 0xF) == 0:
        #         count += 1
        # return count

        return sum(1 for index in range(_CASCADE_COUNT) if self.cascade_length(index) == 0)

    def move_cascade_to_freecell(self, cascade_index: int, freecell_index: int) -> "PackedState":
        return move_packed_cascade_to_freecell(self, cascade_index, freecell_index)

    def move_freecell_to_cascade(self, freecell_index: int, cascade_index: int) -> "PackedState":
        return move_packed_freecell_to_cascade(self, freecell_index, cascade_index)

    def move_cascade_to_foundation(self, cascade_index: int) -> "PackedState":
        return move_packed_cascade_to_foundation(self, cascade_index)

    def move_freecell_to_foundation(self, freecell_index: int) -> "PackedState":
        return move_packed_freecell_to_foundation(self, freecell_index)

    def move_cascade_to_cascade(self, source_index: int, destination_index: int, count: int = 1) -> "PackedState":
        return move_packed_cascade_to_cascade(self, source_index, destination_index, count=count)

    def apply_move(self, move: "Move") -> "PackedState":
        return apply_packed_move(self, move)
