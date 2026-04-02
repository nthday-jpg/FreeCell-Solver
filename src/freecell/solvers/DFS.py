from __future__ import annotations

from time import perf_counter

from .base import BaseSolver, RawMove, SolveResult
from ..core import PackedState


class DFSSolver(BaseSolver):
	def __init__(self, max_expansions: int | None = None):
		self.max_expansions = max_expansions

	def solve(self, initial_state: PackedState) -> SolveResult:
		results = self.solve_k(initial_state, k=1)
		if results:
			return results[0]

		return self.build_result(
			solved=False,
			moves=(),
			expanded_nodes=0,
			elapsed_seconds=0.0,
		)

	def solve_k(self, initial_state: PackedState, k: int = 1) -> tuple[SolveResult, ...]:
		if k <= 0:
			raise ValueError("k must be a positive integer")

		started = perf_counter()
		solutions: list[SolveResult] = []
		expanded_nodes = 0
		stop_search = False
		best_move_count: int | None = None
		best_depth: dict[tuple, int] = {}
		path_keys: set[tuple] = set()
		path_moves: list[RawMove] = []

		def dfs(state: PackedState, prev_move: RawMove | None, depth: int) -> None:
			nonlocal expanded_nodes
			nonlocal stop_search
			nonlocal best_move_count

			if stop_search:
				return

			if self.max_expansions is not None and expanded_nodes >= self.max_expansions:
				stop_search = True
				return

			if best_move_count is not None and depth >= best_move_count:
				return

			key = state.canonical_key()
			if key in path_keys:
				return

			known_depth = best_depth.get(key)
			if known_depth is not None and depth >= known_depth:
				return
			best_depth[key] = depth

			expanded_nodes += 1

			if self.is_goal(state):
				best_move_count = depth
				solutions.append(
					self.build_result(
						solved=True,
						moves=tuple(self._raw_move_to_move(move) for move in path_moves),
						expanded_nodes=expanded_nodes,
						elapsed_seconds=perf_counter() - started,
					)
				)
				if len(solutions) >= k:
					stop_search = True
				return

			path_keys.add(key)
			try:
				for move in self.iter_legal_moves(state):
					if stop_search:
						break
					if prev_move is not None and self._is_reversal(prev_move, move):
						continue
					next_depth = depth + 1
					if best_move_count is not None and next_depth >= best_move_count:
						continue

					path_moves.append(move)
					next_state = self.transition(state, move, validate=False)
					dfs(next_state, move, next_depth)
					path_moves.pop()
			finally:
				path_keys.discard(key)

		dfs(initial_state, prev_move=None, depth=0)

		return tuple(solutions)
