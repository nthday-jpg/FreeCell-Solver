from collections import deque
from time import perf_counter


from .base import BaseSolver, SolveResult, RawMove
from ..core.move_engine import CASCADE, FREECELL, FOUNDATION
from ..core import PackedState, Move


class BFSSolver(BaseSolver):
    def __init__(self, max_expansions: int | None = None):
        super().__init__()
        self.max_expansions = max_expansions

    def solve(self, initial_state: PackedState) -> SolveResult:
        started = perf_counter()
        if self.is_goal(initial_state):
            return self.build_result(
                solved=True,
                moves=(),
                expanded_nodes=0,
                elapsed_seconds=perf_counter() - started,
            )

        queue: deque[PackedState] = deque((initial_state,))
        visited: set[tuple] = {initial_state.canonical_key()}
        parents: dict[PackedState, PackedState | None] = {initial_state: None}
        parent_moves: dict[PackedState, RawMove] = {}

        expanded_nodes = 0

        while queue:

            state = queue.popleft()
            expanded_nodes += 1
            if self.max_expansions is not None and expanded_nodes >= self.max_expansions:
                break
            
            for move in self.iter_legal_moves(state):
                next_state = self.transition(state, move, validate=False)
                next_key = next_state.canonical_key()
                if next_key in visited:
                    continue

                visited.add(next_key)
                parents[next_state] = state
                parent_moves[next_state] = move

                if self.is_goal(next_state):
                    return self.build_result(
                        solved=True,
                        moves=self._reconstruct_moves(next_state, parents, parent_moves),
                        expanded_nodes=expanded_nodes,
                        elapsed_seconds=perf_counter() - started,
                    )

                queue.append(next_state)

        return self.build_result(
            solved=False,
            moves=(),
            expanded_nodes=expanded_nodes,
            elapsed_seconds=perf_counter() - started,
        )
    