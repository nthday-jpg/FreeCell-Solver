from collections import deque
from time import perf_counter


from .base import BaseSolver, SolveResult
from ..core import PackedState, Move


class BFSSolver(BaseSolver):

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
        visited: set[PackedState] = {initial_state}
        parents: dict[PackedState, PackedState | None] = {initial_state: None}
        parent_moves: dict[PackedState, Move] = {}

        expanded_nodes = 0

        while queue:

            state = queue.popleft()
            expanded_nodes += 1
            
            for move in self.iter_legal_moves(state):
                next_state = self.transition(state, move)
                if next_state in visited:
                    continue

                visited.add(next_state)
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

    @staticmethod
    def _reconstruct_moves(
        goal_state: PackedState,
        parents: dict[PackedState, PackedState | None],
        parent_moves: dict[PackedState, Move],
    ) -> tuple[Move, ...]:
        moves_reversed: list[Move] = []
        current = goal_state

        while True:
            move = parent_moves.get(current)
            if move is None:
                break
            moves_reversed.append(move)
            parent = parents[current]
            if parent is None:
                break
            current = parent

        moves_reversed.reverse()
        return tuple(moves_reversed)

    