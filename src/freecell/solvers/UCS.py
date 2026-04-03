import heapq
from time import perf_counter
from itertools import count

from .BestFS import BestFSSolver
from .base import SolveResult, RawMove
from ..core.move_engine import CASCADE, FREECELL, FOUNDATION
from ..core import PackedState, Move

class UCSSolver(BestFSSolver):
    def evaluate(
        self, 
        parent_g: int, 
        move: RawMove | None,
        state: PackedState,
    ) -> tuple[int, int]:
        """
        Calculates f(n) = g(n).
        g: number of moves taken from start.
        """
        # 1. Calculate the 'Step Cost' (Weight)
        weight = 1
        if move:
            # Move format: (src, src_idx, dst, dst_idx, count)
            src, src_idx, dst, dst_idx, count = move
            if dst == FOUNDATION:
                weight = 0 # Encouraged
            elif dst == FREECELL:
                weight = 4 # Discouraged (resource consumption)
            elif dst == CASCADE:
                # Check if column is empty
                if state.cascade_length(dst_idx) == count:
                    if count == 1:
                        weight = 4 # Waste an empty column just to move one card
                    else:
                        weight = 1 # Moving multiple cards to an empty column is fine
                else:
                    weight = 2 # Moving multiple cards to a non-empty column is fine
            
            # Move multiple cards to structure the cascade is good
            if src == CASCADE and dst == CASCADE and count > 1:
                weight = max(1, weight - 1)
        new_g = parent_g + weight
        return (new_g, weight)