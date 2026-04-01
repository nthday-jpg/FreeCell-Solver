from abc import abstractmethod
import heapq
from time import perf_counter
from itertools import count

from .base import BaseSolver, SolveResult, RawMove
from ..core import PackedState

class BestFSSolver(BaseSolver):
    def __init__(self, max_expansions: int | None = None):
        self.max_expansions = max_expansions
    @abstractmethod
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
        Return f_next and new true cost
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

        # Priority Queue: (f_score, g_score, entry_count, state)
        # entry_count acts as a tie-breaker for states with equal f_scores
        tie = count()
        frontier = []
        
        # Initial g is 0. Initial f depends on the heuristic.
        initial_f, _ = self.evaluate(0, None, initial_state)
        heapq.heappush(frontier, (initial_f, 0, next(tie), initial_state))
        
        # Track the best (shortest) distance by canonical state key.
        g_score: dict[tuple, int] = {initial_state.canonical_key(): 0}
        parents: dict[PackedState, PackedState | None] = {initial_state: None}
        parent_moves: dict[PackedState, RawMove] = {}

        expanded_nodes = 0

        while frontier:
            # Pop the "best choice" (lowest f-score)
            _, current_g, _, state = heapq.heappop(frontier)
            state_key = state.canonical_key()
            best_g = g_score.get(state_key)
            if best_g is None or current_g != best_g:
                continue

            if self.is_goal(state):
                return self.build_result(
                    solved=True,
                    moves=self._reconstruct_moves(state, parents, parent_moves),
                    expanded_nodes=expanded_nodes,
                    elapsed_seconds=perf_counter() - started
                )

            expanded_nodes += 1
            if(self.max_expansions is not None and expanded_nodes >= self.max_expansions):
                return self.build_result(
                    solved=False,
                    moves=(),
                    expanded_nodes=expanded_nodes,
                    elapsed_seconds=perf_counter() - started
                )
            prev_move = parent_moves.get(state)

            for move in self.iter_legal_moves(state):
                # Pruning: Prevent immediate reversal (Move A->B then B->A)
                if prev_move and self._is_reversal(prev_move, move):
                    continue

                next_state = self.transition(state, move, validate=False)
       
                f_next, weight = self.evaluate(current_g, move, next_state)
                next_g = current_g + weight
                next_key = next_state.canonical_key()
                # If this is a new state or a shorter path to an existing state
                if next_g < g_score.get(next_key, float("inf")):
                    g_score[next_key] = next_g
                    parents[next_state] = state
                    parent_moves[next_state] = move
                    heapq.heappush(frontier, (f_next, next_g, next(tie), next_state))

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