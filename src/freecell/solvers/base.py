from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
import tracemalloc
from typing import Iterator

from ..core.rules import can_move_to_foundation, can_stack_on_cascade, is_descending_alternating, max_movable_cards
from ..core.state import GameState, Move


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


class BaseSolver(ABC):
	@abstractmethod
	def solve(self, initial_state: GameState) -> SolveResult:
		"""
            
		"""

	def timed_solve(self, initial_state: GameState) -> SolveResult:
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

	def is_goal(self, state: GameState) -> bool:
		return state.is_victory

	def transition(self, state: GameState, move: Move) -> GameState:
		return state.apply_move(move)

	def legal_moves(self, state: GameState) -> tuple[Move, ...]:
		return tuple(self.iter_legal_moves(state))

	def iter_legal_moves(self, state: GameState) -> Iterator[Move]:
		# Prefer foundation moves first to reduce branching in common strategies.
		yield from self._cascade_to_foundation_moves(state)
		yield from self._freecell_to_foundation_moves(state)
		yield from self._freecell_to_cascade_moves(state)
		yield from self._cascade_to_cascade_moves(state)
		yield from self._cascade_to_freecell_moves(state)

	def _cascade_to_foundation_moves(self, state: GameState) -> Iterator[Move]:
		for source_index, cascade in enumerate(state.cascades):
			if not cascade:
				continue
			top = cascade[-1]
			if can_move_to_foundation(top, state.foundation_rank(top.suit)):
				yield Move(
					source="cascade",
					source_index=source_index,
					destination="foundation",
					destination_index=0,
				)

	def _freecell_to_foundation_moves(self, state: GameState) -> Iterator[Move]:
		for source_index, card in enumerate(state.freecells):
			if card is None:
				continue
			if can_move_to_foundation(card, state.foundation_rank(card.suit)):
				yield Move(
					source="freecell",
					source_index=source_index,
					destination="foundation",
					destination_index=0,
				)

	def _cascade_to_freecell_moves(self, state: GameState) -> Iterator[Move]:
		empty_targets = [idx for idx, card in enumerate(state.freecells) if card is None]
		if not empty_targets:
			return
		first_empty = empty_targets[0]
		for source_index, cascade in enumerate(state.cascades):
			if cascade:
				yield Move(
					source="cascade",
					source_index=source_index,
					destination="freecell",
					destination_index=first_empty,
				)

	def _freecell_to_cascade_moves(self, state: GameState) -> Iterator[Move]:
		for source_index, card in enumerate(state.freecells):
			if card is None:
				continue
			for destination_index, destination in enumerate(state.cascades):
				dest_top = destination[-1] if destination else None
				if can_stack_on_cascade(card, dest_top):
					yield Move(
						source="freecell",
						source_index=source_index,
						destination="cascade",
						destination_index=destination_index,
					)

	def _cascade_to_cascade_moves(self, state: GameState) -> Iterator[Move]:
		for source_index, source in enumerate(state.cascades):
			if not source:
				continue
			for destination_index, destination in enumerate(state.cascades):
				if source_index == destination_index:
					continue

				destination_is_empty = len(destination) == 0
				auxiliary_empty_cascades = state.empty_cascade_count() - (1 if destination_is_empty else 0)
				max_count = min(
					len(source),
					max_movable_cards(state.empty_freecell_count(), auxiliary_empty_cascades),
				)

				for count in range(1, max_count + 1):
					moving_stack = source[-count:]
					if not is_descending_alternating(moving_stack):
						continue

					destination_top = destination[-1] if destination else None
					if can_stack_on_cascade(moving_stack[0], destination_top):
						yield Move(
							source="cascade",
							source_index=source_index,
							destination="cascade",
							destination_index=destination_index,
							count=count,
						)

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
