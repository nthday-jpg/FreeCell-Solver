from abc import abstractmethod
import heapq
from time import perf_counter
from itertools import count
from typing import Callable

from .base import BaseSolver, SolveResult, RawMove
from ..core import PackedState

class BestFSSolver(BaseSolver):
    @abstractmethod
    def evaluate(self, 
        g: int, 
        state: PackedState, 
    ) -> int:
        """
        Calculates f(n) = g(n) + h(n).
        g: number of moves taken from start.
        h: estimated moves to goal.
        """
        # 1. Higher foundation count reduces cost
        foundation_count = self.get_foundation_count(state) 
        # 2. Empty freecells are good for mobility
        empty_freecells = self.get_empty_freecells(state)
        # 3. Blocked cards (cards in cascades that are not in order)
        misplaced_cards = self.get_misplaced_count(state)
        h = (52 - foundation_count) * 1.5  # Weight foundation highly
        h += misplaced_cards * 2
        h -= empty_freecells * 3
        return g + h