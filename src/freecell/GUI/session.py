from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from freecell.core import GameState, Move


@dataclass
class GameSession:
    state: GameState
    seed: int | None

    def __init__(self, initial_state: GameState, seed: int | None = None) -> None:
        self.state = initial_state
        self.seed = seed
        self._history: list[GameState] = [initial_state]
        self._cursor = 0
        self._started_at = perf_counter()
        self._victory_time: float | None = None

    @classmethod
    def from_seed(cls, seed: int | None) -> "GameSession":
        return cls(GameState.initial(seed=seed), seed=seed)

    @property
    def move_count(self) -> int:
        return self._cursor

    @property
    def elapsed_seconds(self) -> float:
        if self._victory_time is not None:
            return self._victory_time - self._started_at
        return perf_counter() - self._started_at

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._history) - 1

    def restart(self) -> None:
        self.state = GameState.initial(seed=self.seed)
        self._history = [self.state]
        self._cursor = 0
        self._started_at = perf_counter()
        self._victory_time = None

    def apply_move(self, move: Move) -> tuple[bool, str]:
        try:
            next_state = self.state.apply_move(move)
        except ValueError as error:
            return False, str(error)

        if self.can_redo:
            self._history = self._history[: self._cursor + 1]

        self._history.append(next_state)
        self._cursor += 1
        self.state = next_state
        
        if self.state.is_victory and self._victory_time is None:
            self._victory_time = perf_counter()
            
        return True, ""

    def undo(self) -> bool:
        if not self.can_undo:
            return False
        self._cursor -= 1
        self.state = self._history[self._cursor]
        if not self.state.is_victory:
            self._victory_time = None
        return True

    def redo(self) -> bool:
        if not self.can_redo:
            return False
        self._cursor += 1
        self.state = self._history[self._cursor]
        return True
