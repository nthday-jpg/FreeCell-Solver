from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
import tracemalloc
from typing import Iterator

from ..core.constants import EMPTY_CARD_CODE, RawMove
from ..core.card import card_code_suit_index
from ..core.move_engine import CASCADE, FREECELL, FOUNDATION
from ..core.packed_state import PackedState
from ..core.rules import (
	can_move_to_foundation_code,
	can_stack_on_cascade_code,
	is_descending_alternating_codes,
	max_movable_cards,
)
from ..core.state import Move


@dataclass(frozen=True, slots=True)
class SolveResult:
	solved: bool
	moves: tuple[Move, ...]
	elapsed_seconds: float
	peak_memory_usage: float
	expanded_nodes: int


	@property
	def move_count(self) -> int:
		return len(self.moves)

	def __str__(self) -> str:
		return (
			f"SolveResult(solved={self.solved}, "
			f"move_count={self.move_count}, "
			f"expanded_nodes={self.expanded_nodes}, "
			f"elapsed_seconds={self.elapsed_seconds:.3f}, "
			f"peak_memory_mb={self.peak_memory_usage / (1024 * 1024):.2f})"
		)

class BaseSolver(ABC):
	@abstractmethod
	def solve(self, initial_state: PackedState) -> SolveResult:
		"""
            
		"""

	def timed_solve(self, initial_state: PackedState) -> SolveResult:
		tracemalloc.start()
		started = perf_counter()
		result = self.solve(initial_state)
		elapsed = perf_counter() - started
		_, peak_memory_bytes = tracemalloc.get_traced_memory()
		tracemalloc.stop()
		return SolveResult(
			solved=result.solved,
			moves=result.moves,
			elapsed_seconds=elapsed,
			peak_memory_usage=max(result.peak_memory_usage, float(peak_memory_bytes)),
			expanded_nodes=result.expanded_nodes,
		)

	def is_goal(self, state: PackedState) -> bool:
		return state.is_victory

	def transition(self, state: PackedState, move: RawMove, *, validate: bool = True) -> PackedState:
		return state.apply_raw_move(move, validate=validate)


	def iter_legal_moves(self, state: PackedState) -> Iterator[RawMove]:
		# Prefer foundation moves first to reduce branching in common strategies.
		yield from self._cascade_to_foundation_moves(state)
		yield from self._freecell_to_foundation_moves(state)
		yield from self._freecell_to_cascade_moves(state)
		yield from self._cascade_to_cascade_moves(state)
		yield from self._cascade_to_freecell_moves(state)


	def _reconstruct_moves(self,
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

	def _cascade_to_foundation_moves(self, state: PackedState) -> Iterator[RawMove]:
		for source_index in range(state.cascade_count):
			top_code = state.cascade_top(source_index)
			if top_code is None:
				continue
			suit_index = card_code_suit_index(top_code)
			if can_move_to_foundation_code(top_code, state.foundation_rank(suit_index)):
				yield (CASCADE, source_index, FOUNDATION, 0, 1)

	def _freecell_to_foundation_moves(self, state: PackedState) -> Iterator[RawMove]:
		for source_index in range(state.freecell_slot_count):
			card_code = state.freecell(source_index)
			if card_code == EMPTY_CARD_CODE:
				continue
			suit_index = card_code_suit_index(card_code)
			if can_move_to_foundation_code(card_code, state.foundation_rank(suit_index)):
				yield (FREECELL, source_index, FOUNDATION, 0, 1)

	def _cascade_to_freecell_moves(self, state: PackedState) -> Iterator[RawMove]:
		empty_targets = [idx for idx in range(state.freecell_slot_count) if state.freecell(idx) == EMPTY_CARD_CODE]
		if not empty_targets:
			return
		first_empty = empty_targets[0]
		for source_index in range(state.cascade_count):
			if state.cascade_length(source_index) > 0:
				yield (CASCADE, source_index, FREECELL, first_empty, 1)

	def _freecell_to_cascade_moves(self, state: PackedState) -> Iterator[RawMove]:
		for source_index in range(state.freecell_slot_count):
			card_code = state.freecell(source_index)
			if card_code == EMPTY_CARD_CODE:
				continue
			for destination_index in range(state.cascade_count):
				destination_top_code = state.cascade_top(destination_index)
				if can_stack_on_cascade_code(card_code, destination_top_code):
					yield (FREECELL, source_index, CASCADE, destination_index, 1)

	def _cascade_to_cascade_moves(self, state: PackedState) -> Iterator[RawMove]:
		empty_cascades_total = state.cascade_count_empty()
		empty_freecells_total = state.freecell_count_empty()
		cascade_lengths = [state.cascade_length(i) for i in range(state.cascade_count)]

		for source_index, source_len in enumerate(cascade_lengths):
			if source_len == 0:
				continue
			for destination_index, destination_len in enumerate(cascade_lengths):
				if source_index == destination_index:
					continue

				destination_is_empty = destination_len == 0
				destination_top_code = state.cascade_top(destination_index)
				auxiliary_empty_cascades = empty_cascades_total - (1 if destination_is_empty else 0)
				max_count = min(
					source_len,
					max_movable_cards(empty_freecells_total, auxiliary_empty_cascades),
				)

				for count in range(1, max_count + 1):
					moving_stack = state.cascade_tail_codes(source_index, count)
					if not is_descending_alternating_codes(moving_stack):
						continue
					moving_code = moving_stack[0]

					if can_stack_on_cascade_code(moving_code, destination_top_code):
						yield (CASCADE, source_index, CASCADE, destination_index, count)

	@staticmethod
	def build_result(
		solved: bool,
		moves: tuple[Move, ...],
		expanded_nodes: int,
		elapsed_seconds: float = 0.0,
		peak_memory_usage: float = 0.0,
	) -> SolveResult:
		return SolveResult(
			solved=solved,
			moves=moves,
			elapsed_seconds=elapsed_seconds,
			peak_memory_usage=peak_memory_usage,
			expanded_nodes=expanded_nodes,
		)
