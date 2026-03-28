from __future__ import annotations

from time import perf_counter

from .base import BaseSolver, RawMove
from ..core.move_engine import CASCADE, FREECELL, FOUNDATION
from ..core import PackedState, Move


StateKey = tuple[int, ...]


class IDSSolver(BaseSolver):


    def __init__(self, max_depth: int | None = 200, max_expansions: int | None = None):
        self.max_depth = max_depth
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

        expanded_nodes = [0]
        max_d = self.max_depth if self.max_depth is not None else 10**9

        for depth_limit in range(max_d + 1):
            best_depth: dict[StateKey, int] = {}
            path_keys: set[StateKey] = set()

            raw_moves = self._depth_limited_search(
                initial_state,
                depth_limit,
                depth_from_root=0,
                path_keys=path_keys,
                best_depth=best_depth,
                prev_move=None,
                expanded_nodes=expanded_nodes,
            )

            if raw_moves is not None:
                return self.build_result(
                    solved=True,
                    moves=tuple(self._raw_move_to_move(m) for m in raw_moves),
                    expanded_nodes=expanded_nodes[0],
                    elapsed_seconds=perf_counter() - started,
                )

            if self.max_expansions is not None and expanded_nodes[0] >= self.max_expansions:
                break

        return self.build_result(
            solved=False,
            moves=(),
            expanded_nodes=expanded_nodes[0],
            elapsed_seconds=perf_counter() - started,
        )

    def _depth_limited_search(
        self,
        state: PackedState,
        depth_remaining: int,
        depth_from_root: int,
        path_keys: set[StateKey],
        best_depth: dict[StateKey, int],
        prev_move: RawMove | None,
        expanded_nodes: list[int],
    ) -> tuple[RawMove, ...] | None:
        key = state.key()

        if self.is_goal(state):
            expanded_nodes[0] += 1
            return ()

        if key in path_keys:
            return None

        best = best_depth.get(key)
        if best is not None and depth_from_root >= best:
            return None

        best_depth[key] = depth_from_root

        if depth_remaining == 0:
            expanded_nodes[0] += 1
            return None

        expanded_nodes[0] += 1
        if self.max_expansions is not None and expanded_nodes[0] > self.max_expansions:
            return None

        path_keys.add(key)
        try:
            for move in self.iter_legal_moves(state):
                if prev_move is not None and self._is_reversal(prev_move, move):
                    continue
                next_state = self.transition(state, move, validate=False)
                sub = self._depth_limited_search(
                    next_state,
                    depth_remaining - 1,
                    depth_from_root + 1,
                    path_keys,
                    best_depth,
                    move,
                    expanded_nodes,
                )
                if sub is not None:
                    return (move,) + sub
            return None
        finally:
            path_keys.discard(key)

    @staticmethod
    def _is_reversal(prev: RawMove, cur: RawMove) -> bool:
        p_src, p_si, p_dst, p_di, p_c = prev
        c_src, c_si, c_dst, c_di, c_c = cur
        return (
            c_src == p_dst
            and c_si == p_di
            and c_dst == p_src
            and c_di == p_si
            and c_c == p_c
        )

    @staticmethod
    def _raw_move_to_move(raw: RawMove) -> Move:
        source, source_index, destination, destination_index, count = raw
        source_name = (
            "cascade" if source == CASCADE else "freecell" if source == FREECELL else "foundation"
        )
        destination_name = (
            "cascade"
            if destination == CASCADE
            else "freecell"
            if destination == FREECELL
            else "foundation"
        )
        return Move(
            source=source_name,
            source_index=source_index,
            destination=destination_name,
            destination_index=destination_index,
            count=count,
        )
