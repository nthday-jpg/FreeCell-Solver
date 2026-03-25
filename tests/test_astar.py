from pathlib import Path
from random import seed
import sys
from collections import deque
from time import perf_counter
from statistics import mean, median, stdev

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from freecell.core import *
from freecell.solvers.Astar import AstarSolver


def benchmark_bfs_expansions(seed: int, target_expansions: int):
    cascades = deal_cascades(seed)
    init = GameState(cascades).to_packed()
    solver = AstarSolver(max_expansions=target_expansions)
    solver.solve(init)


def main() -> None:
    seed = 1
    target_expansions = 10000000
    warmup_runs = 1
    measured_runs = 5

    for run_index in range(1, warmup_runs + 1):
        print(f"warmup {run_index}/{warmup_runs}")
        benchmark_bfs_expansions(seed=seed, target_expansions=target_expansions)

    for run_index in range(1, measured_runs + 1):
        print(f"trial {run_index}/{measured_runs}")
        benchmark_bfs_expansions(seed=seed, target_expansions=target_expansions)



if __name__ == "__main__":
    main()