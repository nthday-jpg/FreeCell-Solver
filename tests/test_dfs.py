from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core.state import GameState
from freecell.solvers.DFS import DFSSolver


def run_seed_10(k: int) -> None:
    initial = GameState.initial(seed=10).to_packed()
    solver = DFSSolver(max_expansions=100_000)
    results = solver.solve_k(initial, k=k)

    print(f"seed=10 requested_k={k} found={len(results)}")

    if not results:
        print("no_solution_within_limit=True")
        return

    for idx, result in enumerate(results, start=1):
        print(
            f"solution={idx} elapsed={result.elapsed_seconds:.3f}s "
            f"moves={result.move_count} expanded={result.expanded_nodes}"
        )

        current = initial
        for move in result.moves:
            current = current.apply_move(move)
        assert current.is_victory, f"Solution {idx} did not reach victory"

    print("all_solutions_verified=True")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DFS from seed 10 and collect k solutions")
    parser.add_argument("--k", type=int, default=1, help="Number of solutions to find")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_seed_10(k=args.k)
