from __future__ import annotations

import argparse
import heapq
import sys
from collections import deque
from collections.abc import Callable, Hashable
from itertools import count
from pathlib import Path
from statistics import mean
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core import GameState, PackedState, RawMove
from freecell.solvers.Astar import AstarSolver
from freecell.solvers.BFS import BFSSolver


def run_probe(seed: int, target_expansions: int, mode: str) -> tuple[int, int, float]:
    initial = GameState.initial(seed=seed).to_packed()
    solver = BFSSolver()
    queue: deque[PackedState] = deque([initial])

    key_fn: Callable[[PackedState], Hashable]
    if mode == "canonical":
        key_fn = lambda s: s.canonical_key()
    elif mode == "raw":
        key_fn = lambda s: s.key()
    else:
        raise ValueError(f"Unknown mode: {mode}")

    seen = {key_fn(initial)}
    expanded = 0

    started = perf_counter()
    while queue and expanded < target_expansions:
        state = queue.popleft()
        expanded += 1

        for move in solver.iter_legal_moves(state):
            next_state = solver.transition(state, move, validate=False)
            next_key = key_fn(next_state)
            if next_key in seen:
                continue
            seen.add(next_key)
            queue.append(next_state)

    elapsed = perf_counter() - started
    return expanded, len(seen), elapsed


def _is_reversal(previous_move: RawMove, current_move: RawMove) -> bool:
    return (
        current_move[0] == previous_move[2]
        and current_move[1] == previous_move[3]
        and current_move[2] == previous_move[0]
        and current_move[3] == previous_move[1]
        and current_move[4] == previous_move[4]
    )


def run_astar_to_solution(
    seed: int,
    mode: str,
    max_expansions: int = 50_000,
) -> tuple[bool, int, int, float]:
    initial = GameState.initial(seed=seed).to_packed()
    solver = AstarSolver(max_expansions=max_expansions)

    key_fn: Callable[[PackedState], Hashable]
    if mode == "canonical":
        key_fn = lambda s: s.canonical_key()
    elif mode == "raw":
        key_fn = lambda s: s.key()
    else:
        raise ValueError(f"Unknown mode: {mode}")

    tie = count()
    frontier: list[tuple[float, int, int, PackedState]] = []
    initial_f, _ = solver.evaluate(0, None, initial)
    heapq.heappush(frontier, (initial_f, 0, next(tie), initial))

    g_score: dict[tuple, int] = {key_fn(initial): 0}
    parents: dict[PackedState, PackedState | None] = {initial: None}
    parent_moves: dict[PackedState, RawMove] = {}

    expanded_nodes = 0
    started = perf_counter()

    while frontier:
        _, current_g, _, state = heapq.heappop(frontier)
        state_key = key_fn(state)
        best_g = g_score.get(state_key)
        if best_g is None or current_g != best_g:
            continue

        if state.is_victory:
            elapsed = perf_counter() - started
            # Move count via parent chain length.
            move_count = 0
            cursor = state
            while parent_moves.get(cursor) is not None:
                move_count += 1
                parent = parents[cursor]
                if parent is None:
                    break
                cursor = parent
            return True, expanded_nodes, move_count, elapsed

        expanded_nodes += 1
        if expanded_nodes >= max_expansions:
            return False, expanded_nodes, 0, perf_counter() - started

        prev_move = parent_moves.get(state)
        for move in solver.iter_legal_moves(state):
            if prev_move is not None and _is_reversal(prev_move, move):
                continue

            next_state = solver.transition(state, move, validate=False)
            f_next, weight = solver.evaluate(current_g, move, next_state)
            next_g = current_g + weight
            next_key = key_fn(next_state)
            if next_g < g_score.get(next_key, float("inf")):
                g_score[next_key] = next_g
                parents[next_state] = state
                parent_moves[next_state] = move
                heapq.heappush(frontier, (f_next, next_g, next(tie), next_state))

    return False, expanded_nodes, 0, perf_counter() - started


def benchmark(seed: int = 1, target_expansions: int = 2500, trials: int = 7) -> None:
    raw_times: list[float] = []
    canonical_times: list[float] = []

    # Warmup both code paths once.
    run_probe(seed=seed, target_expansions=400, mode="raw")
    run_probe(seed=seed, target_expansions=400, mode="canonical")

    for _ in range(trials):
        raw_expanded, raw_unique, raw_elapsed = run_probe(
            seed=seed,
            target_expansions=target_expansions,
            mode="raw",
        )
        can_expanded, can_unique, can_elapsed = run_probe(
            seed=seed,
            target_expansions=target_expansions,
            mode="canonical",
        )

        raw_times.append(raw_elapsed)
        canonical_times.append(can_elapsed)

    raw_mean = mean(raw_times)
    canonical_mean = mean(canonical_times)
    speedup = (raw_mean / canonical_mean) if canonical_mean > 0 else 0.0

    print("=== Canonicalization Benchmark (BFS Probe) ===")
    print(f"seed={seed} target_expansions={target_expansions} trials={trials}")
    print(f"raw_mean={raw_mean:.6f}s")
    print(f"canonical_mean={canonical_mean:.6f}s")
    print(f"speedup_raw_over_canonical={speedup:.3f}x")
    print("Interpretation: >1.0 means canonical mode was faster.")


def benchmark_astar_solution(seed: int = 1, trials: int = 5, max_expansions: int = 50_000) -> None:
    raw_times: list[float] = []
    canonical_times: list[float] = []
    raw_expanded_nodes: list[int] = []
    canonical_expanded_nodes: list[int] = []

    # Warmup both code paths once.
    run_astar_to_solution(seed=seed, mode="raw", max_expansions=min(max_expansions, 2_000))
    run_astar_to_solution(seed=seed, mode="canonical", max_expansions=min(max_expansions, 2_000))

    for _ in range(trials):
        raw_solved, raw_expanded, _, raw_elapsed = run_astar_to_solution(
            seed=seed,
            mode="raw",
            max_expansions=max_expansions,
        )
        can_solved, can_expanded, _, can_elapsed = run_astar_to_solution(
            seed=seed,
            mode="canonical",
            max_expansions=max_expansions,
        )

        if raw_solved != can_solved:
            raise AssertionError(
                "A* solved status differs between raw and canonical modes. "
                f"raw={raw_solved}, canonical={can_solved}"
            )

        raw_times.append(raw_elapsed)
        canonical_times.append(can_elapsed)
        raw_expanded_nodes.append(raw_expanded)
        canonical_expanded_nodes.append(can_expanded)

    raw_mean = mean(raw_times)
    canonical_mean = mean(canonical_times)
    speedup = (raw_mean / canonical_mean) if canonical_mean > 0 else 0.0

    print("=== Canonicalization Benchmark (A* Time To First Solution) ===")
    print(f"seed={seed} trials={trials} max_expansions={max_expansions}")
    print(f"raw_mean_time={raw_mean:.6f}s")
    print(f"canonical_mean_time={canonical_mean:.6f}s")
    print(f"mean_expanded_raw={mean(raw_expanded_nodes):.1f}")
    print(f"mean_expanded_canonical={mean(canonical_expanded_nodes):.1f}")
    print(f"speedup_raw_over_canonical={speedup:.3f}x")
    print("Interpretation: >1.0 means canonical mode was faster.")


def difference_test(seeds: tuple[int, ...] = (1, 2, 3, 4, 5), target_expansions: int = 1500, max_expansions: int = 50_000) -> None:
    """
    Checks that canonical and raw modes produce measurable differences while preserving solve status.
    Raises AssertionError if no meaningful difference is detected in the tested seeds.
    """
    bfs_difference_found = False

    for seed in seeds:
        _, raw_unique, _ = run_probe(seed=seed, target_expansions=target_expansions, mode="raw")
        _, can_unique, _ = run_probe(seed=seed, target_expansions=target_expansions, mode="canonical")
        if can_unique < raw_unique:
            bfs_difference_found = True
            break

    if not bfs_difference_found:
        raise AssertionError(
            "Difference test failed: canonical BFS probe did not reduce unique states for tested seeds."
        )

    raw_solved, raw_expanded, _, _ = run_astar_to_solution(
        seed=seeds[0], mode="raw", max_expansions=max_expansions
    )
    can_solved, can_expanded, _, _ = run_astar_to_solution(
        seed=seeds[0], mode="canonical", max_expansions=max_expansions
    )

    if raw_solved != can_solved:
        raise AssertionError(
            "Difference test failed: A* solved status differs between raw and canonical modes."
        )
    if can_expanded > raw_expanded:
        raise AssertionError(
            "Difference test failed: canonical A* expanded more states than raw mode."
        )

    print("=== Difference Test ===")
    print("PASS: canonical mode shows measurable BFS dedup difference and preserves A* solve status.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark canonical vs raw state keys.")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--trials", type=int, default=7)
    parser.add_argument("--target-expansions", type=int, default=2500)
    parser.add_argument("--max-expansions", type=int, default=50_000)
    parser.add_argument("--skip-difference-test", action="store_true")
    args = parser.parse_args()

    benchmark(
        seed=args.seed,
        target_expansions=args.target_expansions,
        trials=args.trials,
    )
    benchmark_astar_solution(
        seed=args.seed,
        trials=max(3, min(args.trials, 9)),
        max_expansions=args.max_expansions,
    )
    if not args.skip_difference_test:
        difference_test(max_expansions=args.max_expansions)


if __name__ == "__main__":
    main()
