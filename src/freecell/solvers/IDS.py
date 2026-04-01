from __future__ import annotations

from collections.abc import Callable, Iterator
from time import perf_counter

from .base import BaseSolver, RawMove, SolveResult
from ..core import PackedState


StateKey = tuple[int, tuple[int, ...], tuple[int, ...]]


class IDSSolver(BaseSolver):


    def __init__(
        self,
        max_depth: int | None = 200,
        max_expansions: int | None = None,
        depth_limit_scheduler: Callable[[int], int] | None = None,
    ):
        self.max_depth = max_depth
        self.max_expansions = max_expansions
        self.depth_limit_scheduler = depth_limit_scheduler

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
        for depth_limit in self._iter_depth_limits():
            best_depth: dict[StateKey, int] = {}
            path_keys: set[StateKey] = set()
            parents: dict[PackedState, PackedState | None] = {initial_state: None}
            parent_moves: dict[PackedState, RawMove] = {}

            goal_state = self._depth_limited_search(
                initial_state,
                depth_limit,
                depth_from_root=0,
                path_keys=path_keys,
                best_depth=best_depth,
                prev_move=None,
                expanded_nodes=expanded_nodes,
                parents=parents,
                parent_moves=parent_moves,
            )

            if goal_state is not None:
                return self.build_result(
                    solved=True,
                    moves=self._reconstruct_moves(goal_state, parents, parent_moves),
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

    def _iter_depth_limits(self) -> Iterator[int]:
        if self.depth_limit_scheduler is None:
            max_d = self.max_depth if self.max_depth is not None else 10**9
            yield from range(max_d + 1)
            return

        previous_depth = -1
        step = 0
        while True:
            depth_limit = self.depth_limit_scheduler(step)
            if depth_limit < 0:
                raise ValueError("depth_limit_scheduler must return non-negative depth limits")
            if depth_limit <= previous_depth:
                raise ValueError("depth_limit_scheduler must return strictly increasing depth limits")
            if self.max_depth is not None and depth_limit > self.max_depth:
                return
            yield depth_limit
            previous_depth = depth_limit
            step += 1

    def _depth_limited_search(
        self,
        state: PackedState,
        depth_remaining: int,
        depth_from_root: int,
        path_keys: set[StateKey],
        best_depth: dict[StateKey, int],
        prev_move: RawMove | None,
        expanded_nodes: list[int],
        parents: dict[PackedState, PackedState | None],
        parent_moves: dict[PackedState, RawMove],
    ) -> PackedState | None:
        key = state.canonical_key()

        if self.is_goal(state):
            expanded_nodes[0] += 1
            return state

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
                parents[next_state] = state
                parent_moves[next_state] = move
                sub = self._depth_limited_search(
                    next_state,
                    depth_remaining - 1,
                    depth_from_root + 1,
                    path_keys,
                    best_depth,
                    move,
                    expanded_nodes,
                    parents,
                    parent_moves,
                )
                if sub is not None:
                    return sub
            return None
        finally:
            path_keys.discard(key)
