from .BestFS import BestFSSolver
from ..core.move_engine import FREECELL, FOUNDATION
from .base import RawMove
from ..core import PackedState
from ..core.rules import is_descending_alternating_codes

class AstarSolver(BestFSSolver):
    def evaluate(
        self, 
        parent_g: int, 
        move: RawMove | None,
        state: PackedState,
    ) -> tuple[float, int]:
        """
        Calculates f(n) = g(n) + h(n).
        g: number of moves taken from start.
        h: estimated moves to goal.
        """
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
        remain_cards = state.cards_remaining()
        # 2. Empty freecells are good for mobility
        empty_freecells = state.freecell_count_empty()
        occupied_FC = state.freecell_slot_count - empty_freecells
        disorder = self._calculate_disorder(state)
        h = remain_cards + occupied_FC + disorder
        return (new_g + h*1.5, weight)


    def _calculate_disorder(self, state: PackedState) -> int:
        total_disorder = 0
        for c_idx in range(state.cascade_count):
            length = state.cascade_length(c_idx)
            if length <= 1:
                continue
                
            # Get all card codes in this cascade at once
            # This is much faster than calling a method for every single card
            cards = state.cascade_tail_codes(c_idx, length)
            
            for i in range(length - 1):
                # Check the pair: cards[i] and cards[i+1]
                # We pass a slice of 2 cards to your existing rule checker
                if not is_descending_alternating_codes(cards[i : i+2]):
                    # If they don't match, everything below index 'i' is disordered
                    total_disorder += (length - i - 1)
                    break                 
        return total_disorder