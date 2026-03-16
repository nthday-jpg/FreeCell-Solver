from dataclasses import dataclass
from typing import Literal

from .card import Card, SUIT_TO_INDEX, SUITS
from .deal_generator import deal_cascades
from .packed_state import PackedState

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

    def to_packed(self) -> PackedState:
        return PackedState.from_game_state(self)

    @classmethod
    def from_packed(cls, packed_state: PackedState) -> "GameState":
        return packed_state.to_game_state()
    
    @property
    def is_victory(self) -> bool:
        return self.to_packed().is_victory

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
        return self.to_packed().move_cascade_to_freecell(cascade_index, freecell_index).to_game_state()

    def move_freecell_to_cascade(self, freecell_index: int, cascade_index: int) -> "GameState":
        return self.to_packed().move_freecell_to_cascade(freecell_index, cascade_index).to_game_state()

    def move_cascade_to_foundation(self, cascade_index: int) -> "GameState":
        return self.to_packed().move_cascade_to_foundation(cascade_index).to_game_state()

    def move_freecell_to_foundation(self, freecell_index: int) -> "GameState":
        return self.to_packed().move_freecell_to_foundation(freecell_index).to_game_state()

    def move_cascade_to_cascade(self, source_index: int, destination_index: int, count: int = 1) -> "GameState":
        return self.to_packed().move_cascade_to_cascade(source_index, destination_index, count=count).to_game_state()

    def apply_move(self, move: Move) -> "GameState":
        return self.to_packed().apply_move(move).to_game_state()

    def foundation_complete(self) -> bool:
        return self.to_packed().is_victory

    def foundation_summary(self) -> dict[str, int]:
        return {suit: self.foundations[idx] for idx, suit in enumerate(SUITS)}
