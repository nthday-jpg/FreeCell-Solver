import sys
import argparse
from pathlib import Path
from time import perf_counter
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core import GameState, deal_cascades
from freecell.solvers.BFS import BFSSolver
from freecell.solvers.IDS import IDSSolver
from freecell.solvers.UCS import UCSSolver
from freecell.solvers.Astar import AstarSolver

def evaluate_solver(solver_class, solver_name: str, seeds: list[int], max_expansions: int):
    results = {
        "solved": 0,
        "times": [],
        "expansions": [],
        "memories": [],
        "move_counts": []
    }
    print(f"\n[{solver_name}] Testing {len(seeds)} problems (Limits: {max_expansions} expansions)")
    
    for s in seeds:
        print(f"  -> seed={s:02d} | ", end="", flush=True)
        init = GameState(deal_cascades(s)).to_packed()
        
        solver = solver_class()
        if hasattr(solver, "max_expansions"):
            solver.max_expansions = max_expansions
        # Use timed_solve to capture peak memory via tracemalloc
        res = solver.timed_solve(init)
        
        results["times"].append(res.elapsed_seconds)
        results["expansions"].append(res.expanded_nodes)
        results["memories"].append(res.peak_memory_usage)
        
        mem_mb = res.peak_memory_usage / (1024 * 1024)
        
        if res.solved:
            results["solved"] += 1
            results["move_counts"].append(res.move_count)
            print(f"SOLVED: \ttime={res.elapsed_seconds:.3f}s \tnodes={res.expanded_nodes} \tmem={mem_mb:.2f}MB \tmoves={res.move_count}")
        else:
            print(f"FAILED: \ttime={res.elapsed_seconds:.3f}s \tnodes={res.expanded_nodes} \tmem={mem_mb:.2f}MB (Hit Limit)")
            
    return results


def plot_results(data: dict, seeds: list[int], max_expansions: int):
    solvers = list(data.keys())
    solve_rates = [(data[s]["solved"] / len(seeds)) * 100 for s in solvers]
    avg_times = [mean(data[s]["times"]) for s in solvers]
    avg_nodes = [mean(data[s]["expansions"]) for s in solvers]
    avg_memories = [mean(data[s]["memories"]) / (1024 * 1024) for s in solvers] # MB
    
    avg_moves = []
    for s in solvers:
        if len(data[s]["move_counts"]) > 0:
            avg_moves.append(mean(data[s]["move_counts"]))
        else:
            avg_moves.append(0)

    # Save a CSV dump for easy copy-pasting to report tables FIRST
    with open("tests/evaluation_data.csv", "w", encoding="utf-8") as f:
        f.write("Algorithm,SolveRate(%),AvgSearchTime(s),AvgPeakMemory(MB),AvgExpandedNodes,AvgSearchLength(moves)\n")
        for i, s in enumerate(solvers):
            f.write(f"{s},{solve_rates[i]:.1f},{avg_times[i]:.4f},{avg_memories[i]:.2f},{avg_nodes[i]:.1f},{avg_moves[i]:.1f}\n")
    print(f"[+] Raw data saved to 'tests/evaluation_data.csv' for Word/Latex tables.")

def main():
    parser = argparse.ArgumentParser(description="Evaluate all search algorithms.")
    parser.add_argument("--start", type=int, default=1, help="Starting seed number")
    parser.add_argument("--count", type=int, default=10, help="Number of seeds to test")
    parser.add_argument("--limit", type=int, default=50000, help="Max expansions per algorithm per seed")
    args = parser.parse_args()

    seeds = list(range(args.start, args.start + args.count))
    max_expansions = args.limit
    
    print("=" * 60)
    print(" FREECELL SOLVER MASS BENCHMARK SUITE")
    print("=" * 60)
    
    data = {}
    # data["BFS"] = evaluate_solver(BFSSolver, "BFS", seeds, max_expansions)
    # # data["IDS"] = evaluate_solver(IDSSolver, "IDS", seeds, max_expansions)
    # data["UCS"] = evaluate_solver(UCSSolver, "UCS", seeds, max_expansions)
    data["A*"] = evaluate_solver(AstarSolver, "A*", seeds, max_expansions)
    
    plot_results(data, seeds, max_expansions)

if __name__ == "__main__":
    main()
