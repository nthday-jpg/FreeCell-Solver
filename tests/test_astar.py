from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from freecell.core import *
from freecell.solvers.Astar import AstarSolver
from freecell.solvers.base import SolveResult


def benchmark_astar_expansions(seed_value: int, target_expansions: int) -> SolveResult:
    cascades = deal_cascades(seed_value)
    init = GameState(cascades).to_packed()
    solver = AstarSolver(max_expansions=target_expansions)
    return solver.solve(init)


def main() -> None:
    start_seed = 10
    target_expansions = 10000000
    warmup_runs = 0
    measured_runs = 10
    current_seed = start_seed

    for run_index in range(1, warmup_runs + 1):
        result = benchmark_astar_expansions(seed_value=current_seed, target_expansions=target_expansions)
        print(
            f"warmup {run_index}/{warmup_runs} seed={current_seed} "
            f"solved={result.solved} expanded={result.expanded_nodes} "
            f"moves={result.move_count} elapsed={result.elapsed_seconds:.3f}s"
        )
        current_seed += 1

    for run_index in range(1, measured_runs + 1):
        result = benchmark_astar_expansions(seed_value=current_seed, target_expansions=target_expansions)
        print(
            f"trial {run_index}/{measured_runs} seed={current_seed} "
            f"solved={result.solved} expanded={result.expanded_nodes} "
            f"moves={result.move_count} elapsed={result.elapsed_seconds:.3f}s"
        )
        current_seed += 1



if __name__ == "__main__":
    main()