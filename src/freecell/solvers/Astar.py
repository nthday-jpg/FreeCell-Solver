from abc import abstractmethod
import heapq
from time import perf_counter
from itertools import count
from typing import Callable

from freecell.solvers.BestFS import BestFSSolver
from ..core.move_engine import CASCADE, FREECELL, FOUNDATION
from .base import BaseSolver, SolveResult, RawMove
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
        foundation_count = self.get_foundation_count(state) 
        # 2. Empty freecells are good for mobility
        empty_freecells = self.get_empty_freecells(state)
        # 3. Blocked cards (cards in cascades that are not in order)
        misplaced_cards = self.get_misplaced_count(state)
        h = (52 - foundation_count) * 1.5  # Weight foundation highly
        h += misplaced_cards * 2
        h -= empty_freecells * 3
        return (new_g + h, weight)