from __future__ import annotations

from dataclasses import dataclass
from math import exp, log
import os
from random import Random
from statistics import mean
from time import perf_counter
from typing import Callable, cast
from joblib import Parallel, delayed, effective_n_jobs

from freecell.core.state import GameState
from freecell.solvers.BFS import BFSSolver


@dataclass(frozen=True)
class PolicyConfig:
	start_seed: int
	deal_count: int
	max_depth: int
	max_states_per_depth: int
	dedupe_by_canonical_key: bool
	layer_sample_seed: int
	move_order_seed: int
	n_jobs: int = -1


RANDOM_ORDER_CONFIG = PolicyConfig(
    start_seed=1,
    deal_count=100,               # Higher seed count is critical for variance
    max_depth=100,            # FreeCell games often settle around depth 10-15
    max_states_per_depth=10000, 
    dedupe_by_canonical_key=True,
    layer_sample_seed=2026,
    move_order_seed=2027,    # Essential: shuffle move_list before sampling
	n_jobs=-1,
)

MY_ORDER_CONFIG = PolicyConfig(
    start_seed=1,
    deal_count=50,
    max_depth=100,
    max_states_per_depth=20000, 
    dedupe_by_canonical_key=True,
    layer_sample_seed=2026,
    move_order_seed=2027,    # Keep your fixed priority order
	n_jobs=-1,
)


ENABLE_PRE_RUN_TEST = True
PRE_RUN_TEST_SEED_COUNT = 3


PolicyMoveOrder = Callable[[list, Random], list]


@dataclass
class DepthRow:
	depth: int
	expanded_states: int
	avg_legal_moves: float
	unique_next_states: int
	next_per_state_ratio: float


@dataclass
class PolicySummary:
	policy_name: str
	rows: list[DepthRow]


def _reservoir_append(
	reservoir: list,
	item,
	*,
	seen_count: int,
	limit: int,
	rng: Random,
) -> None:
	if limit <= 0:
		reservoir.append(item)
		return

	if seen_count <= limit:
		reservoir.append(item)
		return

	replace_index = rng.randrange(seen_count)
	if replace_index < limit:
		reservoir[replace_index] = item


def keep_my_order(moves: list, _: Random) -> list:
	return moves


def shuffle_random_order(moves: list, rng: Random) -> list:
	rng.shuffle(moves)
	return moves


def estimate_branch_factor_for_seed(
	seed: int,
	*,
	max_depth: int,
	max_states_per_depth: int,
	dedupe: bool,
	rng_sample_layer: Random,
	rng_move_order: Random,
	move_order_fn: PolicyMoveOrder,
) -> list[DepthRow]:
	solver = BFSSolver()
	initial = GameState.initial(seed=seed).to_packed()

	current_layer = [initial]
	seen: set[tuple] = {initial.canonical_key()} if dedupe else set()
	rows: list[DepthRow] = []

	for depth in range(max_depth):
		if not current_layer:
			break

		layer = current_layer
		next_layer_sample = []
		legal_moves_total = 0
		next_states_seen = 0

		for state in layer:
			legal_moves = list(solver.iter_legal_moves(state))
			legal_moves = move_order_fn(legal_moves, rng_move_order)
			legal_moves_total += len(legal_moves)

			for move in legal_moves:
				child = state.apply_raw_move(move, validate=False)
				if dedupe:
					key = child.canonical_key()
					if key in seen:
						continue
					seen.add(key)
				next_states_seen += 1
				_reservoir_append(
					next_layer_sample,
					child,
					seen_count=next_states_seen,
					limit=max_states_per_depth,
					rng=rng_sample_layer,
				)

		expanded_states = len(layer)
		avg_legal_moves = (legal_moves_total / expanded_states) if expanded_states else 0.0
		unique_next_states = next_states_seen
		ratio = (unique_next_states / expanded_states) if expanded_states else 0.0

		rows.append(
			DepthRow(
				depth=depth,
				expanded_states=expanded_states,
				avg_legal_moves=avg_legal_moves,
				unique_next_states=unique_next_states,
				next_per_state_ratio=ratio,
			)
		)

		# Drop previous layer and keep only sampled next states.
		current_layer = next_layer_sample

	return rows


def geometric_mean(values: list[float]) -> float:
	filtered = [v for v in values if v > 0.0]
	if not filtered:
		return 0.0
	return exp(mean(log(v) for v in filtered))


def summarize(all_seed_rows: list[list[DepthRow]]) -> list[DepthRow]:
	if not all_seed_rows:
		return []

	max_depth_seen = max((rows[-1].depth for rows in all_seed_rows if rows), default=-1)
	summary: list[DepthRow] = []

	for depth in range(max_depth_seen + 1):
		depth_rows = [rows[depth] for rows in all_seed_rows if len(rows) > depth]
		if not depth_rows:
			continue

		summary.append(
			DepthRow(
				depth=depth,
				expanded_states=int(mean(r.expanded_states for r in depth_rows)),
				avg_legal_moves=mean(r.avg_legal_moves for r in depth_rows),
				unique_next_states=int(mean(r.unique_next_states for r in depth_rows)),
				next_per_state_ratio=mean(r.next_per_state_ratio for r in depth_rows),
			)
		)

	return summary


def _run_seed_once(
	seed: int,
	*,
	config: PolicyConfig,
	move_order_fn: PolicyMoveOrder,
) -> list[DepthRow]:
	# Derive deterministic per-seed RNG streams so results are stable across parallel runs.
	rng_sample_layer = Random(config.layer_sample_seed + seed * 1009)
	rng_move_order = Random(config.move_order_seed + seed * 9176)
	return estimate_branch_factor_for_seed(
		seed,
		max_depth=config.max_depth,
		max_states_per_depth=config.max_states_per_depth,
		dedupe=config.dedupe_by_canonical_key,
		rng_sample_layer=rng_sample_layer,
		rng_move_order=rng_move_order,
		move_order_fn=move_order_fn,
	)


def _run_seed_once_timed(
	seed: int,
	*,
	config: PolicyConfig,
	move_order_fn: PolicyMoveOrder,
) -> tuple[list[DepthRow], float, int]:
	started = perf_counter()
	rows = _run_seed_once(seed, config=config, move_order_fn=move_order_fn)
	elapsed = perf_counter() - started
	expanded_nodes = sum(row.expanded_states for row in rows)
	return rows, elapsed, expanded_nodes


def _format_eta(seconds: float) -> str:
	if seconds < 60:
		return f"{seconds:.1f}s"
	minutes, rem = divmod(seconds, 60)
	if minutes < 60:
		return f"{int(minutes)}m {rem:.0f}s"
	hours, rem_minutes = divmod(minutes, 60)
	return f"{int(hours)}h {int(rem_minutes)}m"


def print_pre_run_estimate(
	policy_name: str,
	*,
	move_order_fn: PolicyMoveOrder,
	config: PolicyConfig,
) -> None:
	test_seed_count = min(config.deal_count, PRE_RUN_TEST_SEED_COUNT)
	if test_seed_count <= 0:
		return

	test_seeds = range(config.start_seed, config.start_seed + test_seed_count)
	test_workers = min(max(1, effective_n_jobs(config.n_jobs)), test_seed_count)

	test_rows = cast(
		list[tuple[list[DepthRow], float, int]],
		Parallel(n_jobs=test_workers, backend="loky")(
			delayed(_run_seed_once_timed)(
				seed,
				config=config,
				move_order_fn=move_order_fn,
			)
			for seed in test_seeds
		),
	)

	total_elapsed = sum(row[1] for row in test_rows)
	total_nodes = sum(row[2] for row in test_rows)
	avg_seed_elapsed = total_elapsed / test_seed_count if test_seed_count else 0.0
	avg_seed_nodes = total_nodes / test_seed_count if test_seed_count else 0.0
	nodes_per_sec = (total_nodes / total_elapsed) if total_elapsed > 0 else 0.0

	full_workers = min(max(1, effective_n_jobs(config.n_jobs)), max(1, config.deal_count), os.cpu_count() or 1)
	estimated_total_nodes = avg_seed_nodes * config.deal_count
	estimated_wall_seconds = (avg_seed_elapsed * config.deal_count) / full_workers if full_workers else 0.0

	print(f"Pre-run test [{policy_name}]")
	print(
		f"- sampled {test_seed_count} seed(s): "
		f"avg_nodes/seed={avg_seed_nodes:,.0f}, avg_time/seed={avg_seed_elapsed:.2f}s"
	)
	print(f"- estimated nodes/sec: {nodes_per_sec:,.0f}")
	print(
		f"- projected full run: seeds={config.deal_count}, "
		f"workers~{full_workers}, est_nodes~{estimated_total_nodes:,.0f}, "
		f"est_wall~{_format_eta(estimated_wall_seconds)}"
	)
	print()


def run_policy(
	policy_name: str,
	*,
	move_order_fn: PolicyMoveOrder,
	config: PolicyConfig,
) -> PolicySummary:
	seeds = range(config.start_seed, config.start_seed + config.deal_count)
	all_seed_rows = cast(
		list[list[DepthRow]],
		Parallel(n_jobs=config.n_jobs, backend="loky")(
			delayed(_run_seed_once)(
				seed,
				config=config,
				move_order_fn=move_order_fn,
			)
			for seed in seeds
		),
	)

	return PolicySummary(policy_name=policy_name, rows=summarize(all_seed_rows))


def print_report(summary_rows: list[DepthRow], *, policy_name: str) -> None:
	print(f"Branch factor estimate (Kaggle-friendly) - {policy_name}")
	print("=" * 80)
	print(
		f"{'depth':>5} {'avg_states':>12} {'avg_legal_moves':>16} "
		f"{'avg_unique_next':>16} {'next/state':>12}"
	)
	print("-" * 80)

	for row in summary_rows:
		print(
			f"{row.depth:>5} "
			f"{row.expanded_states:>12} "
			f"{row.avg_legal_moves:>16.3f} "
			f"{row.unique_next_states:>16} "
			f"{row.next_per_state_ratio:>12.3f}"
		)

	depth_means = [r.avg_legal_moves for r in summary_rows]
	unique_ratios = [r.next_per_state_ratio for r in summary_rows]
	print("\nOverall estimates")
	print(f"- Mean legal-move branching factor: {mean(depth_means):.3f}" if depth_means else "- n/a")
	print(
		f"- Geometric mean legal-move branching factor: {geometric_mean(depth_means):.3f}"
		if depth_means
		else "- n/a"
	)
	print(
		f"- Mean unique-child branching factor: {mean(unique_ratios):.3f}"
		if unique_ratios
		else "- n/a"
	)
	print(
		f"- Geometric mean unique-child branching factor: {geometric_mean(unique_ratios):.3f}"
		if unique_ratios
		else "- n/a"
	)


def print_policy_comparison(policy_summaries: list[PolicySummary]) -> None:
	print("\nPolicy comparison (overall means)")
	print("=" * 80)
	print(f"{'policy':<16} {'mean_legal_bf':>15} {'mean_unique_bf':>15}")
	print("-" * 80)

	for policy in policy_summaries:
		depth_means = [r.avg_legal_moves for r in policy.rows]
		unique_ratios = [r.next_per_state_ratio for r in policy.rows]
		mean_legal = mean(depth_means) if depth_means else 0.0
		mean_unique = mean(unique_ratios) if unique_ratios else 0.0
		print(f"{policy.policy_name:<16} {mean_legal:>15.3f} {mean_unique:>15.3f}")


def main() -> None:
	if ENABLE_PRE_RUN_TEST:
		print_pre_run_estimate(
			"my_order",
			move_order_fn=keep_my_order,
			config=MY_ORDER_CONFIG,
		)
		print_pre_run_estimate(
			"random_order",
			move_order_fn=shuffle_random_order,
			config=RANDOM_ORDER_CONFIG,
		)

	print("Configuration")
	print("- my_order config:")
	print(f"    start_seed={MY_ORDER_CONFIG.start_seed}")
	print(f"    deal_count={MY_ORDER_CONFIG.deal_count}")
	print(f"    max_depth={MY_ORDER_CONFIG.max_depth}")
	print(f"    max_states_per_depth={MY_ORDER_CONFIG.max_states_per_depth}")
	print(f"    dedupe_by_canonical_key={MY_ORDER_CONFIG.dedupe_by_canonical_key}")
	print(f"    layer_sample_seed={MY_ORDER_CONFIG.layer_sample_seed}")
	print(f"    move_order_seed={MY_ORDER_CONFIG.move_order_seed}")
	print(f"    n_jobs={MY_ORDER_CONFIG.n_jobs}")
	print("- random_order config:")
	print(f"    start_seed={RANDOM_ORDER_CONFIG.start_seed}")
	print(f"    deal_count={RANDOM_ORDER_CONFIG.deal_count}")
	print(f"    max_depth={RANDOM_ORDER_CONFIG.max_depth}")
	print(f"    max_states_per_depth={RANDOM_ORDER_CONFIG.max_states_per_depth}")
	print(f"    dedupe_by_canonical_key={RANDOM_ORDER_CONFIG.dedupe_by_canonical_key}")
	print(f"    layer_sample_seed={RANDOM_ORDER_CONFIG.layer_sample_seed}")
	print(f"    move_order_seed={RANDOM_ORDER_CONFIG.move_order_seed}")
	print(f"    n_jobs={RANDOM_ORDER_CONFIG.n_jobs}")
	print()

	my_order_summary = run_policy(
		"my_order",
		move_order_fn=keep_my_order,
		config=MY_ORDER_CONFIG,
	)

	random_order_summary = run_policy(
		"random_order",
		move_order_fn=shuffle_random_order,
		config=RANDOM_ORDER_CONFIG,
	)

	policy_summaries = [my_order_summary, random_order_summary]
	for policy in policy_summaries:
		print_report(policy.rows, policy_name=policy.policy_name)
		print()

	print_policy_comparison(policy_summaries)


if __name__ == "__main__":
	main()
