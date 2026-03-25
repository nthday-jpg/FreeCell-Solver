from .BestFS import BestFSSolver
from ..core.move_engine import FREECELL, FOUNDATION
from .base import RawMove
from ..core import PackedState

class AstarSolver(BestFSSolver):
    def evaluate(
        self, 
        parent_g: int, 
        move: RawMove | None,
        state: PackedState,
    ) -> tuple[int, int]:
        """
        Calculates f(n) = g(n) + h(n).
        g: number of moves taken from start.
        h: estimated moves to goal.
        """
        gamestate = state.to_game_state()
        # 1. Calculate the 'Step Cost' (Weight)
        weight = 1
        if move:
            # Move format: (src, src_idx, dst, dst_idx, count)
            _, _, dst, _, _ = move
            if dst == FOUNDATION:
                weight = 1 # Encouraged
            elif dst == FREECELL:
                weight = 3 # Discouraged (resource consumption)
        new_g = parent_g + weight
        # 1. Higher foundation count reduces cost
        remain_cards = gamestate.cards_remaining
        # 2. Empty freecells are good for mobility
        empty_freecells = gamestate.empty_freecell_count()
        # 3. Blocked cards (cards in cascades that are not in order)
        misplaced_cards = gamestate.disorder_count()
        h = remain_cards + misplaced_cards - empty_freecells
        return (new_g + h * 2, weight)