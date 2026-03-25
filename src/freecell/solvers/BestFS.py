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
        heuristic: Callable[[PackedState], int] | None
    ) -> int:
        """
        Calculates f(n) = g(n) + h(n).
        g: number of moves taken from start.
        h: estimated moves to goal.
        """
        pass

    def solve(self, initial_state: PackedState) -> SolveResult:
        started = perf_counter()
        
        if self.is_goal(initial_state):
            return self.build_result(
                solved=True,
                moves=(),
                expanded_nodes=0,
                elapsed_seconds=perf_counter() - started
            )

        # Priority Queue: (f_score, entry_count, state)
        # entry_count acts as a tie-breaker for states with equal f_scores
        tie = count()
        frontier = []
        
        # Initial g is 0. Initial f depends on the heuristic.
        initial_f = self.evaluate(0, initial_state, self.heuristic)
        heapq.heappush(frontier, (initial_f, next(tie), initial_state))
        
        # Track the best (shortest) distance to each state
        g_score: dict[PackedState, int] = {initial_state: 0}
        parents: dict[PackedState, PackedState | None] = {initial_state: None}
        parent_moves: dict[PackedState, RawMove] = {}

        expanded_nodes = 0

        while frontier:
            # Pop the "best choice" (lowest f-score)
            _, _, state = heapq.heappop(frontier)

            if self.is_goal(state):
                return self.build_result(
                    solved=True,
                    moves=self._reconstruct_moves(state, parents, parent_moves),
                    expanded_nodes=expanded_nodes,
                    elapsed_seconds=perf_counter() - started
                )

            expanded_nodes += 1
            current_g = g_score[state]
            prev_move = parent_moves.get(state)

            for move in self.iter_legal_moves(state):
                # Pruning: Prevent immediate reversal (Move A->B then B->A)
                if prev_move and self._is_reversal(prev_move, move):
                    continue

                next_state = self.transition(state, move, validate=False)
                # For optimal path, each move costs 1
                tentative_g = current_g + 1 # Modify cost function

                # If this is a new state or a shorter path to an existing state
                if next_state not in g_score or tentative_g < g_score[next_state]:
                    g_score[next_state] = tentative_g
                    parents[next_state] = state
                    parent_moves[next_state] = move
                    
                    # Calculate f-score and push to priority queue
                    f_next = self.evaluate(tentative_g, next_state, self.heuristic)
                    heapq.heappush(frontier, (f_next, next(tie), next_state))

        return self.build_result(
            solved=False,
            moves=(),
            expanded_nodes=expanded_nodes,
            elapsed_seconds=perf_counter() - started
        )

    @staticmethod
    def _is_reversal(p: RawMove, c: RawMove) -> bool:
        # p=previous, c=current. move format: (src, src_idx, dst, dst_idx, count)
        return (c[0] == p[2] and c[1] == p[3] and  # current src is prev dst
                c[2] == p[0] and c[3] == p[1] and  # current dst is prev src
                c[4] == p[4])                      # same card count