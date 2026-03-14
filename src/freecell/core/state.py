from dataclasses import dataclass
from typing import Literal

from .card import Card, SUIT_TO_INDEX, SUITS
from .deal_generator import deal_cascades
from .rules import (
    can_move_to_foundation,
    can_stack_on_cascade,
    is_descending_alternating,
    max_movable_cards,
)

PileType = Literal["cascade", "freecell", "foundation"]


@dataclass(frozen=True, slots=True)
class Move:
    source: PileType
    source_index: int
    destination: PileType
    destination_index: int
    count: int = 1


@dataclass(frozen=True, slots=True)
class GameState:
    cascades: tuple[tuple[Card, ...], ...]
    freecells: tuple[Card | None, ...] = (None, None, None, None)
    foundations: tuple[int, int, int, int] = (0, 0, 0, 0)

    @classmethod
    def initial(cls, seed: int | None = None) -> "GameState":
        return cls(cascades=deal_cascades(seed=seed))
    
    @property
    def is_victory(self) -> bool:
        return self.foundation_complete()

    @property
    def cards_in_foundation(self) -> int:
        return sum(self.foundations)

    @property
    def cards_remaining(self) -> int:
        return 52 - self.cards_in_foundation

    @property
    def progress_ratio(self) -> float:
        # Returns a value between 0.0 and 1.0
        return self.cards_in_foundation / 52.0

    def foundation_rank(self, suit: str) -> int:
        return self.foundations[SUIT_TO_INDEX[suit]]

    def empty_freecell_count(self) -> int:
        return sum(1 for card in self.freecells if card is None)

    def empty_cascade_count(self) -> int:
        return sum(1 for cascade in self.cascades if not cascade)

    def cascade_top(self, index: int) -> Card | None:
        cascade = self.cascades[index]
        return cascade[-1] if cascade else None

    def move_cascade_to_freecell(self, cascade_index: int, freecell_index: int) -> "GameState":
        source = self.cascades[cascade_index]
        if not source:
            raise ValueError("Source cascade is empty")
        if self.freecells[freecell_index] is not None:
            raise ValueError("Destination freecell is occupied")

        card = source[-1]
        new_cascades = list(self.cascades)
        new_cascades[cascade_index] = source[:-1]
        new_freecells = list(self.freecells)
        new_freecells[freecell_index] = card
        return GameState(
            cascades=tuple(new_cascades),
            freecells=tuple(new_freecells),
            foundations=self.foundations,
        )

    def move_freecell_to_cascade(self, freecell_index: int, cascade_index: int) -> "GameState":
        card = self.freecells[freecell_index]
        if card is None:
            raise ValueError("Source freecell is empty")

        destination = self.cascades[cascade_index]
        dest_top = destination[-1] if destination else None
        if not can_stack_on_cascade(card, dest_top):
            raise ValueError("Illegal placement on cascade")

        new_freecells = list(self.freecells)
        new_freecells[freecell_index] = None
        new_cascades = list(self.cascades)
        new_cascades[cascade_index] = destination + (card,)
        return GameState(
            cascades=tuple(new_cascades),
            freecells=tuple(new_freecells),
            foundations=self.foundations,
        )

    def move_cascade_to_foundation(self, cascade_index: int) -> "GameState":
        source = self.cascades[cascade_index]
        if not source:
            raise ValueError("Source cascade is empty")
        card = source[-1]
        suit_idx = SUIT_TO_INDEX[card.suit]
        current_rank = self.foundations[suit_idx]
        if not can_move_to_foundation(card, current_rank):
            raise ValueError("Card cannot be moved to foundation")

        new_cascades = list(self.cascades)
        new_cascades[cascade_index] = source[:-1]
        new_foundations = list(self.foundations)
        new_foundations[suit_idx] = card.rank
        foundations = (
            new_foundations[0],
            new_foundations[1],
            new_foundations[2],
            new_foundations[3],
        )
        return GameState(
            cascades=tuple(new_cascades),
            freecells=self.freecells,
            foundations=foundations,
        )

    def move_freecell_to_foundation(self, freecell_index: int) -> "GameState":
        card = self.freecells[freecell_index]
        if card is None:
            raise ValueError("Source freecell is empty")

        suit_idx = SUIT_TO_INDEX[card.suit]
        current_rank = self.foundations[suit_idx]
        if not can_move_to_foundation(card, current_rank):
            raise ValueError("Card cannot be moved to foundation")

        new_freecells = list(self.freecells)
        new_freecells[freecell_index] = None
        new_foundations = list(self.foundations)
        new_foundations[suit_idx] = card.rank
        foundations = (
            new_foundations[0],
            new_foundations[1],
            new_foundations[2],
            new_foundations[3],
        )
        return GameState(
            cascades=self.cascades,
            freecells=tuple(new_freecells),
            foundations=foundations,
        )

    def move_cascade_to_cascade(self, source_index: int, destination_index: int, count: int = 1) -> "GameState":
        if count <= 0:
            raise ValueError("count must be positive")
        if source_index == destination_index:
            raise ValueError("Source and destination cascades must differ")

        source = self.cascades[source_index]
        destination = self.cascades[destination_index]
        if len(source) < count:
            raise ValueError("Source cascade does not contain enough cards")

        moving_stack = source[-count:]
        if not is_descending_alternating(moving_stack):
            raise ValueError("Moving stack is not in descending alternating order")

        destination_is_empty = len(destination) == 0
        auxiliary_empty_cascades = self.empty_cascade_count() - (1 if destination_is_empty else 0)
        allowed = max_movable_cards(self.empty_freecell_count(), auxiliary_empty_cascades)
        if count > allowed:
            raise ValueError(f"Cannot move {count} cards with current free space (max {allowed})")

        if not can_stack_on_cascade(moving_stack[0], destination[-1] if destination else None):
            raise ValueError("Illegal placement on destination cascade")

        new_cascades = list(self.cascades)
        new_cascades[source_index] = source[:-count]
        new_cascades[destination_index] = destination + moving_stack
        return GameState(
            cascades=tuple(new_cascades),
            freecells=self.freecells,
            foundations=self.foundations,
        )

    def apply_move(self, move: Move) -> "GameState":
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

    def foundation_complete(self) -> bool:
        return self.foundations == (13, 13, 13, 13)

    def foundation_summary(self) -> dict[str, int]:
        return {suit: self.foundations[idx] for idx, suit in enumerate(SUITS)}
