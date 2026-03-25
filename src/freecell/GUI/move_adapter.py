from __future__ import annotations

from freecell.core import Move, PackedState
from freecell.core.move_engine import CASCADE, FREECELL, FOUNDATION
from freecell.solvers.base import BaseSolver


def _raw_to_move(raw_move: tuple[int, int, int, int, int]) -> Move:
    source, source_index, destination, destination_index, count = raw_move
    source_name = "cascade" if source == CASCADE else "freecell" if source == FREECELL else "foundation"
    destination_name = "cascade" if destination == CASCADE else "freecell" if destination == FREECELL else "foundation"
    return Move(
        source=source_name,
        source_index=source_index,
        destination=destination_name,
        destination_index=destination_index,
        count=count,
    )


def get_legal_moves(state: PackedState) -> tuple[Move, ...]:
    # Reuse canonical move generation from solver base to keep UI behavior aligned with solvers.
    solver = _MoveProbeSolver()
    return tuple(_raw_to_move(raw_move) for raw_move in solver.iter_legal_moves(state))


class _MoveProbeSolver(BaseSolver):
    def solve(self, initial_state: PackedState):
        raise NotImplementedError("Move probe solver does not solve states")
