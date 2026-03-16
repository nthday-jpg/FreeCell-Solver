from pathlib import Path
import sys
from collections import deque
from time import perf_counter
from statistics import mean, median, stdev

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from freecell.core import *
from freecell.solvers.BFS import BFSSolver


def benchmark_bfs_expansions(seed: int, target_expansions: int) -> float:
    cascades = deal_cascades(seed)
    init = GameState(cascades).to_packed()
    solver = BFSSolver()

    visited = set()
    queue: deque = deque([init])
    expanded = 0

    started = perf_counter()
    while queue and expanded < target_expansions:
        state = queue.popleft()
        if state in visited:
            continue
        visited.add(state)
        expanded += 1

        for move in solver.iter_legal_moves(state):
            next_state = solver.transition(state, move)
            if next_state not in visited:
                queue.append(next_state)

    elapsed = perf_counter() - started
    rate = (expanded / elapsed) if elapsed > 0 else 0.0
    print(
        f"seed={seed} expanded={expanded} elapsed={elapsed:.6f}s "
        f"rate={rate:.2f} nodes/s remaining_queue={len(queue)}"
    )
    return elapsed


def main() -> None:
    seed = 1
    target_expansions = 100_000
    warmup_runs = 1
    measured_runs = 5

    for run_index in range(1, warmup_runs + 1):
        print(f"warmup {run_index}/{warmup_runs}")
        benchmark_bfs_expansions(seed=seed, target_expansions=target_expansions)

    elapsed_samples: list[float] = []
    for run_index in range(1, measured_runs + 1):
        print(f"trial {run_index}/{measured_runs}")
        elapsed_samples.append(
            benchmark_bfs_expansions(seed=seed, target_expansions=target_expansions)
        )

    avg = mean(elapsed_samples)
    med = median(elapsed_samples)
    dev = stdev(elapsed_samples) if len(elapsed_samples) > 1 else 0.0
    print(
        f"summary seed={seed} target={target_expansions} runs={measured_runs} "
        f"mean={avg:.6f}s median={med:.6f}s stdev={dev:.6f}s"
    )


if __name__ == "__main__":
    main()