import heapq
from time import perf_counter
from itertools import count

from .base import BaseSolver, SolveResult, RawMove
from ..core.move_engine import CASCADE, FREECELL, FOUNDATION
from ..core import PackedState, Move

class UCSSolver(BaseSolver):
    def __init__(self, max_expansions: int | None = None):
        self.max_expansions = max_expansions

    def solve(self, initial_state: PackedState) -> SolveResult:
        started = perf_counter()
        if self.is_goal(initial_state):
            return self.build_result(
                solved=True,
                moves=(),
                expanded_nodes=0,
                elapsed_seconds=perf_counter() - started
            )
        
        tie = count()
        frontier: list[tuple[int, int, PackedState]] = []
        heapq.heappush(frontier, (0, next(tie), initial_state))
        best_cost: dict[PackedState, int] = {initial_state: 0} # reached
        parents: dict[PackedState, PackedState | None] = {initial_state: None}
        parent_moves: dict[PackedState, RawMove] = {}

        expanded_nodes = 0
        max_exp = self.max_expansions if self.max_expansions is not None else float('inf')

        while frontier:
            current_cost, _, state = heapq.heappop(frontier)

            if expanded_nodes % 5000 == 0 and len(frontier) > 3 * len(best_cost):
                frontier = [e for e in frontier if e[0] == best_cost.get(e[2])]
                heapq.heapify(frontier)

            if current_cost != best_cost.get(state):
                continue
            expanded_nodes += 1

            if expanded_nodes >= max_exp:
                return self.build_result(
                    solved=False,
                    moves=(),
                    expanded_nodes=expanded_nodes,
                    elapsed_seconds=perf_counter() - started,
                    peak_memory_usage=0.0,
                )

            # late goal test
            if self.is_goal(state):
                return self.build_result(
                    solved=True,
                    moves=self._reconstruct_moves(state, parents, parent_moves),
                    expanded_nodes=expanded_nodes,
                    elapsed_seconds=perf_counter() - started
                )
            
            prev_move = parent_moves.get(state)
            for move in self.iter_legal_moves(state):
                # prune immediate inverse moves
                if prev_move is not None:
                    prev_src, prev_src_idx, prev_dst, prev_dst_idx, prev_count = prev_move
                    cur_src, cur_src_idx, cur_dst, cur_dst_idx, cur_count = move

                    # check if move is inverse of previous move
                    if (cur_src == prev_dst and cur_src_idx == prev_dst_idx and
                        cur_dst == prev_src and cur_dst_idx == prev_src_idx and
                        prev_count == cur_count):
                        continue

                next_state = self.transition(state, move, validate=False)
                next_state_cost = current_cost + 1
                if next_state not in best_cost or next_state_cost < best_cost[next_state]:
                    best_cost[next_state] = next_state_cost
                    parents[next_state] = state
                    parent_moves[next_state] = move
                    heapq.heappush(frontier, (next_state_cost, next(tie),next_state))

        return self.build_result(
            solved=False,
            moves=(),
            expanded_nodes=expanded_nodes,
            elapsed_seconds=perf_counter() - started
        )