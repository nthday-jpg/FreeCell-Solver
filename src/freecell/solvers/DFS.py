from __future__ import annotations

import sys
from time import perf_counter

from .base import BaseSolver, RawMove, SolveResult
from ..core import PackedState

sys.setrecursionlimit(10000)


class DFSSolver(BaseSolver):
	def solve(self, initial_state: PackedState) -> SolveResult:
		started = perf_counter()
		results = self.solve_k(initial_state, k=1)
		if results:
			return results[0]

		return self.build_result(
			solved=False,
			moves=(),
			expanded_nodes=getattr(self, '_last_expanded_nodes', 0),
			elapsed_seconds=perf_counter() - started,
		)

	def solve_k(self, initial_state: PackedState, k: int = 1, prune_suboptimal: bool = False) -> tuple[SolveResult, ...]:
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

		# Iterative DFS using explicit stack and initiated tracking
		# Stack elements: (state, depth, prev_move, moves_iterator, initiated)
		stack = [(initial_state, 0, None, iter(self.iter_legal_moves(initial_state)), False)]
		
		while stack and not stop_search:
			if self.max_expansions is not None and expanded_nodes >= self.max_expansions:
				stop_search = True
				break

			state, depth, prev_move, moves_iterator, initiated = stack.pop()

			if not initiated:
				if best_move_count is not None and depth >= best_move_count:
					if depth > 0: path_moves.pop()
					continue

				key = state.canonical_key()
				if key in path_keys:
					if depth > 0: path_moves.pop()
					continue
					
				known_depth = best_depth.get(key)
				if known_depth is not None and depth >= known_depth:
					if depth > 0: path_moves.pop()
					continue

				if len(best_depth) >= 100_000:
					del best_depth[next(iter(best_depth))]
				best_depth[key] = depth

				if self.is_goal(state):
					if prune_suboptimal:
						best_move_count = depth
					solutions.append(
						self.build_result(
							solved=True,
							moves=tuple(self._raw_move_to_move(m) for m in path_moves),
							expanded_nodes=expanded_nodes,
							elapsed_seconds=perf_counter() - started,
						)
					)
					if len(solutions) >= k:
						stop_search = True
					if depth > 0: path_moves.pop()
					continue

				path_keys.add(key)
				expanded_nodes += 1

				# Return self to stack as initiated
				stack.append((state, depth, prev_move, moves_iterator, True))
			else:
				try:
					move = next(moves_iterator)
					if prev_move is not None and self._is_reversal(prev_move, move):
						stack.append((state, depth, prev_move, moves_iterator, True))
						continue
						
					next_depth = depth + 1
					if best_move_count is not None and next_depth >= best_move_count:
						stack.append((state, depth, prev_move, moves_iterator, True))
						continue
						
					path_moves.append(move)
					next_state = self.transition(state, move, validate=False)
					
					stack.append((state, depth, prev_move, moves_iterator, True))
					stack.append((next_state, next_depth, move, iter(self.iter_legal_moves(next_state)), False))
					
				except StopIteration:
					if depth > 0:
						path_moves.pop()
					path_keys.discard(state.canonical_key())

		self._last_expanded_nodes = expanded_nodes
		return tuple(solutions)
