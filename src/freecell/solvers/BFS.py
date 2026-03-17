from collections import deque
from time import perf_counter


from .base import BaseSolver, SolveResult, RawMove
from ..core.move_engine import CASCADE, FREECELL, FOUNDATION
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
        parent_moves: dict[PackedState, RawMove] = {}

        expanded_nodes = 0

        while queue:

            state = queue.popleft()
            expanded_nodes += 1
            
            for move in self.iter_legal_moves(state):
                next_state = self.transition(state, move, validate=False)
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
        parent_moves: dict[PackedState, RawMove],
    ) -> tuple[Move, ...]:
        moves_reversed: list[Move] = []
        current = goal_state

        while True:
            move = parent_moves.get(current)
            if move is None:
                break
            source, source_index, destination, destination_index, count = move
            source_name = "cascade" if source == CASCADE else "freecell" if source == FREECELL else "foundation"
            destination_name = "cascade" if destination == CASCADE else "freecell" if destination == FREECELL else "foundation"
            moves_reversed.append(
                Move(
                    source=source_name,
                    source_index=source_index,
                    destination=destination_name,
                    destination_index=destination_index,
                    count=count,
                )
            )
            parent = parents[current]
            if parent is None:
                break
            current = parent

        moves_reversed.reverse()
        return tuple(moves_reversed)

    