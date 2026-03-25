from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .card import (
    Card,
    card_to_code,
    code_to_card,
)
from .move_engine import (
    apply_packed_move,
    apply_packed_raw_move,
    move_packed_cascade_to_cascade,
    move_packed_cascade_to_foundation,
    move_packed_cascade_to_freecell,
    move_packed_freecell_to_cascade,
    move_packed_freecell_to_foundation,
)

from .constants import (
    CARD_BITS,
    CARD_MASK,
    CASCADE_COUNT,
    FREECELL_COUNT,
    FOUNDATION_COUNT,
    FOUNDATION_BITS,
    CASCADE_LEN_BITS,
    MAX_FOUNDATION_RANK,
    FOUNDATION_COMPLETE_MASK,
    EMPTY_CARD_CODE,
    RawMove
) 

if TYPE_CHECKING:
    from .state import GameState
    from .state import Move


FOUNDATION_BITS = 4
CASCADE_LEN_BITS = 4
MAX_FOUNDATION_RANK = 13
FOUNDATION_COMPLETE_MASK = sum(
    MAX_FOUNDATION_RANK << (i * FOUNDATION_BITS)
    for i in range(FOUNDATION_COUNT)
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

    _hash_cache: int = field(default=0, init=False, repr=False, compare=False, hash=False)
    
    def __post_init__(self) -> None:
        object.__setattr__(self, '_hash_cache', hash((self.cascade_words, self.cascade_lengths, self.freecells, self.foundations)))
    
    def __hash__(self) -> int:
        return self._hash_cache

    @property
    def is_victory(self) -> bool:
        return self.foundations == FOUNDATION_COMPLETE_MASK

    @property
    def cascade_count(self) -> int:
        return CASCADE_COUNT

    @property
    def freecell_slot_count(self) -> int:
        return FREECELL_COUNT
    
    @classmethod
    def from_game_state(cls, state: "GameState") -> "PackedState":
        if len(state.cascades) != CASCADE_COUNT:
            raise ValueError(f"Expected {CASCADE_COUNT} cascades, got {len(state.cascades)}")
        if len(state.freecells) != FREECELL_COUNT:
            raise ValueError(f"Expected {FREECELL_COUNT} freecells, got {len(state.freecells)}")
        if len(state.foundations) != FOUNDATION_COUNT:
            raise ValueError(f"Expected {FOUNDATION_COUNT} foundations, got {len(state.foundations)}")

        cascade_words: list[int] = [0] * CASCADE_COUNT
        cascade_lengths = 0
        for index, cascade in enumerate(state.cascades):
            if len(cascade) > 13:
                raise ValueError("Cascade cannot exceed 13 cards")
            word = 0
            for position, card in enumerate(cascade):
                word |= card_to_code(card) << (position * CARD_BITS)
            cascade_words[index] = word
            cascade_lengths |= len(cascade) << (index * CASCADE_LEN_BITS)

        freecells = 0
        for index, card in enumerate(state.freecells):
            code = EMPTY_CARD_CODE if card is None else card_to_code(card)
            freecells |= code << (index * CARD_BITS)

        foundations = 0
        for index, rank in enumerate(state.foundations):
            if rank < 0 or rank > 13:
                raise ValueError(f"Foundation rank must be between 0 and 13, got {rank}")
            foundations |= rank << (index * FOUNDATION_BITS)

        return cls(
            cascade_words=tuple(cascade_words),
            cascade_lengths=cascade_lengths,
            freecells=freecells,
            foundations=foundations,
        )

    def to_game_state(self) -> "GameState":
        if len(self.cascade_words) != CASCADE_COUNT:
            raise ValueError(f"Expected {CASCADE_COUNT} packed cascade words, got {len(self.cascade_words)}")

        cascades: list[tuple[Card, ...]] = []
        for index in range(CASCADE_COUNT):
            length = self.cascade_length(index)
            cards = tuple(
                code_to_card((self.cascade_words[index] >> (position * CARD_BITS)) & CARD_MASK)
                for position in range(length)
            )
            cascades.append(cards)

        freecells = tuple(
            None if code == EMPTY_CARD_CODE else code_to_card(code)
            for code in (self.freecell(index) for index in range(FREECELL_COUNT))
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
        return (self.cascade_lengths >> (index * CASCADE_LEN_BITS)) & 0xF

    def freecell(self, index: int) -> int:
        return (self.freecells >> (index * CARD_BITS)) & CARD_MASK

    def freecell_count_empty(self) -> int:
        v = self.freecells
        # Identify positions where all 6 bits are 1
        # We shift and AND. If a bit stays 1, it means it and its neighbors were 1.
        all_ones = v & (v >> 1) & (v >> 2) & (v >> 3) & (v >> 4) & (v >> 5)
        
        # The mask 0x41041 aligns with the 1st bit of each 6-bit slot:
        # (1 << 0) | (1 << 6) | (1 << 12) | (1 << 18)
        return (all_ones & 0x41041).bit_count()

        # return sum(1 for index in range(FREECELL_COUNT) if self.freecell(index) == EMPTY_CARD_CODE)

    def cards_remaining(self) -> int:
        v = self.foundations
        # Step 1: Sum adjacent 4-bit fields into 8-bit fields
        # (max value 13+13 = 26, fits in 8 bits)
        v = (v & 0x0F0F) + ((v >> 4) & 0x0F0F)
        
        # Step 2: Sum the two 8-bit fields into the final result
        # (max value 26+26 = 52, fits in 8 bits)
        cards_in_foundation = (v + (v >> 8)) & 0xFF
        
        return 52 - cards_in_foundation

    def foundation_rank(self, suit_index: int) -> int:
        return (self.foundations >> (suit_index * FOUNDATION_BITS)) & 0xF

    def cascade_top(self, index: int) -> int | None:
        length = self.cascade_length(index)
        if length == 0:
            return None
        return (self.cascade_words[index] >> ((length - 1) * CARD_BITS)) & CARD_MASK

    def cascade_card_code(self, cascade_index: int, position: int) -> int:
        length = self.cascade_length(cascade_index)
        if position < 0 or position >= length:
            raise ValueError(f"Position {position} out of bounds for cascade length {length}")
        return (self.cascade_words[cascade_index] >> (position * CARD_BITS)) & CARD_MASK

    def cascade_tail_codes(self, cascade_index: int, count: int) -> tuple[int, ...]:
        length = self.cascade_length(cascade_index)
        if count <= 0:
            raise ValueError("count must be positive")
        if count > length:
            raise ValueError("count exceeds cascade length")
        start = length - count
        # Extract tail as one bit window, then decode each card code in order.
        tail_bits = self.cascade_words[cascade_index] >> (start * CARD_BITS)
        return tuple((tail_bits >> (offset * CARD_BITS)) & CARD_MASK for offset in range(count))

    def cascade_count_empty(self) -> int:
        v = self.cascade_lengths
        # Combine all bits in each 4-bit nibble into the lowest bit of the nibble
        # If any bit was 1, the result's LSB for that nibble will be 1
        any_bit_set = (v | (v >> 1) | (v >> 2) | (v >> 3)) & 0x11111111
        
        # Flip the bits and mask to look at only the LSB of each nibble
        # A '1' now represents a nibble that was originally '0000'
        zero_nibbles = (~any_bit_set) & 0x11111111
        
        # Count the set bits (requires Python 3.10+)
        return zero_nibbles.bit_count()

        # return sum(1 for index in range(CASCADE_COUNT) if self.cascade_length(index) == 0)

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

    def apply_raw_move(self, move: RawMove, *, validate: bool = True) -> "PackedState":
        return apply_packed_raw_move(self, move, validate=validate)
