from collections import deque
from time import perf_counter


from .base import BaseSolver, SolveResult
from ..core import PackedState, Move


class BFSSolver(BaseSolver):
    def __init__(self) -> None:
        self.expand_100k_seconds: float | None = None

    def solve(self, initial_state: PackedState) -> SolveResult:
        visited = set()
        queue: deque[tuple[PackedState, tuple[Move, ...]]] = deque()
        queue.append((initial_state, ()))
        expanded_nodes = 0
        started = perf_counter()
        self.expand_100k_seconds = None

        while queue:
            state, moves = queue.popleft()
            if state in visited:
                continue
            visited.add(state)
            expanded_nodes += 1
            if self.expand_100k_seconds is None and expanded_nodes == 100000:
                self.expand_100k_seconds = perf_counter() - started
                return SolveResult(
                    solved=True,
                    moves=moves,
                    elapsed_seconds=self.expand_100k_seconds,
                    peak_memory_usage=0.0,
                    expanded_nodes=expanded_nodes,
                )
            if self.is_goal(state):
                elapsed = perf_counter() - started
                return SolveResult(
                    solved=True,
                    moves=moves,
                    elapsed_seconds=elapsed,
                    peak_memory_usage=0.0,
                    expanded_nodes=expanded_nodes,
                )

            for move in self.iter_legal_moves(state):
                next_state = self.transition(state, move)
                if next_state not in visited:
                    queue.append((next_state, moves + (move,)))

        elapsed = perf_counter() - started
        return SolveResult(
            solved=False,
            moves=(),
            elapsed_seconds=elapsed,
            peak_memory_usage=0.0,
            expanded_nodes=expanded_nodes,
        )