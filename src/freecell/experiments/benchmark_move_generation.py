from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from random import Random
from statistics import mean, median, stdev
from time import perf_counter_ns
from typing import Callable, Iterable

from ..core.packed_state import PackedState
from ..core.state import GameState
from ..core.move_types import RawMove
from ..solvers.BFS import BFSSolver


@dataclass(slots=True)
class TimingStats:
	name: str
	times_us: list[float]
	move_counts: list[int]

	def avg_time_us(self) -> float:
		return mean(self.times_us)

	def median_time_us(self) -> float:
		return median(self.times_us)

	def p95_time_us(self) -> float:
		if not self.times_us:
			return 0.0
		sorted_values = sorted(self.times_us)
		index = max(0, math.ceil(len(sorted_values) * 0.95) - 1)
		return sorted_values[index]

	def stdev_time_us(self) -> float:
		if len(self.times_us) < 2:
			return 0.0
		return stdev(self.times_us)

	def avg_moves(self) -> float:
		if not self.move_counts:
			return 0.0
		return mean(self.move_counts)


MoveGeneratorFactory = Callable[[], Iterable[RawMove]]


ORDERED_BENCHMARK_NAMES = (
	"all_legal_moves",
	"cascade_to_foundation",
	"freecell_to_foundation",
	"freecell_to_cascade",
	"cascade_to_cascade",
	"cascade_to_freecell",
)


def _count_moves(factory: MoveGeneratorFactory) -> int:
	count = 0
	for _ in factory():
		count += 1
	return count


def _build_benchmarks(solver: BFSSolver, state: PackedState) -> tuple[tuple[str, MoveGeneratorFactory], ...]:
	return (
		("all_legal_moves", lambda: solver.iter_legal_moves(state)),
		("cascade_to_foundation", lambda: solver._cascade_to_foundation_moves(state)),
		("freecell_to_foundation", lambda: solver._freecell_to_foundation_moves(state)),
		("freecell_to_cascade", lambda: solver._freecell_to_cascade_moves(state)),
		("cascade_to_cascade", lambda: solver._cascade_to_cascade_moves(state)),
		("cascade_to_freecell", lambda: solver._cascade_to_freecell_moves(state)),
	)


def _empty_stats_map() -> dict[str, TimingStats]:
	return {name: TimingStats(name, [], []) for name in ORDERED_BENCHMARK_NAMES}


def _state_samples_by_depth(
	initial_state: PackedState,
	*,
	depths: tuple[int, ...],
	rng: Random,
	solver: BFSSolver,
) -> dict[int, PackedState]:
	target_depths = set(depths)
	samples: dict[int, PackedState] = {}

	if 0 in target_depths:
		samples[0] = initial_state

	if not target_depths:
		return samples

	max_depth = max(target_depths)
	current = initial_state
	prev_move: RawMove | None = None

	for depth in range(1, max_depth + 1):
		moves = list(solver.iter_legal_moves(current))
		if prev_move is not None:
			moves = [move for move in moves if not solver._is_reversal(prev_move, move)]

		if not moves:
			break

		selected_move = rng.choice(moves)
		current = current.apply_raw_move(selected_move, validate=False)
		prev_move = selected_move

		if depth in target_depths:
			samples[depth] = current

	return samples


def _benchmark_state(
	solver: BFSSolver,
	state: PackedState,
	*,
	repeats: int,
	warmup: int,
	aggregate: dict[str, TimingStats],
) -> None:
	benchmarks = _build_benchmarks(solver, state)

	for name, factory in benchmarks:
		for _ in range(warmup):
			_count_moves(factory)

		for _ in range(repeats):
			started_ns = perf_counter_ns()
			move_count = _count_moves(factory)
			elapsed_us = (perf_counter_ns() - started_ns) / 1_000.0

			stats = aggregate[name]
			stats.times_us.append(elapsed_us)
			stats.move_counts.append(move_count)


def _print_state_report(state_label: str, stats_by_name: dict[str, TimingStats]) -> None:
	print(f"State group: {state_label}")
	print(
		f"{'benchmark':<24} {'avg_us':>10} {'median_us':>10} {'p95_us':>10} {'stdev_us':>10} {'avg_moves':>10}"
	)
	print("-" * 84)

	for name in ORDERED_BENCHMARK_NAMES:
		stats = stats_by_name[name]
		if not stats.times_us:
			print(f"{name:<24} {'-':>10} {'-':>10} {'-':>10} {'-':>10} {'-':>10}")
			continue

		print(
			f"{name:<24} "
			f"{stats.avg_time_us():>10.2f} "
			f"{stats.median_time_us():>10.2f} "
			f"{stats.p95_time_us():>10.2f} "
			f"{stats.stdev_time_us():>10.2f} "
			f"{stats.avg_moves():>10.2f}"
		)
	print()


def _print_report(
	stats_by_state: dict[str, dict[str, TimingStats]],
	*,
	deals: int,
	repeats: int,
	warmup: int,
	start_seed: int,
	state_depths: tuple[int, ...],
) -> None:
	print("Move generation benchmark")
	print(f"Deals: {deals}, repeats/deal: {repeats}, warmup: {warmup}, start_seed: {start_seed}")
	print(f"State depths (plies): {', '.join(str(depth) for depth in state_depths)}")
	print()
	for state_label in sorted(stats_by_state):
		_print_state_report(state_label, stats_by_state[state_label])

def main() -> None:

    # Benchmark configuration (edit these values directly).
    START_SEED = 1
    DEALS = 50
    REPEATS = 200
    WARMUP = 20
    STATE_DEPTHS = (0, 8, 16)
    STATE_SELECTION_SEED = 42

    state_depths = tuple(sorted(set(STATE_DEPTHS)))

    solver = BFSSolver()
    rng = Random(STATE_SELECTION_SEED)
    stats_by_state: dict[str, dict[str, TimingStats]] = defaultdict(_empty_stats_map)

    for seed in range(START_SEED, START_SEED + DEALS):
        initial_state = GameState.initial(seed=seed).to_packed()
        samples = _state_samples_by_depth(
            initial_state,
            depths=state_depths,
            rng=rng,
            solver=solver,
        )

        for depth in state_depths:
            state = samples.get(depth)
            if state is None:
                continue
            state_label = f"depth_{depth}"
            _benchmark_state(
                solver,
                state,
                repeats=REPEATS,
                warmup=WARMUP,
                aggregate=stats_by_state[state_label],
            )

    _print_report(
        stats_by_state,
        deals=DEALS,
        repeats=REPEATS,
        warmup=WARMUP,
        start_seed=START_SEED,
        state_depths=state_depths,
    )


if __name__ == "__main__":
	main()
