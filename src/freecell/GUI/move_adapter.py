from __future__ import annotations

from freecell.core import Move, PackedState
from freecell.core.move_engine import CASCADE, FREECELL, FOUNDATION
from freecell.core.constants import EMPTY_CARD_CODE
from freecell.core.rules import can_stack_on_cascade_code
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
    raw_moves = list(solver.iter_legal_moves(state))
    
    empty_freecells = [idx for idx in range(state.freecell_slot_count) if state.freecell(idx) == EMPTY_CARD_CODE]
    
    # The solver only emits moves to empty_freecells[0]. The UI needs moves to all empty_freecells.
    if len(empty_freecells) > 1:
        first_empty = empty_freecells[0]
        extra_moves = []
        for rm in raw_moves:
            source, src_idx, dest, dest_idx, count = rm
            if dest == FREECELL and dest_idx == first_empty:
                for other_empty in empty_freecells[1:]:
                    extra_moves.append((source, src_idx, FREECELL, other_empty, count))
        raw_moves.extend(extra_moves)
        
    # Foundation extraction
    for suit_index in range(4):
        rank = state.foundation_rank(suit_index)
        if rank > 0:
            card_code = ((rank - 1) << 2) | suit_index
            for dest_index in range(state.cascade_count):
                if can_stack_on_cascade_code(card_code, state.cascade_top(dest_index)):
                    raw_moves.append((FOUNDATION, suit_index, CASCADE, dest_index, 1))
            for empty_idx in empty_freecells:
                raw_moves.append((FOUNDATION, suit_index, FREECELL, empty_idx, 1))

    return tuple(_raw_to_move(raw_move) for raw_move in raw_moves)


class _MoveProbeSolver(BaseSolver):
    def solve(self, initial_state: PackedState):
        raise NotImplementedError("Move probe solver does not solve states")
