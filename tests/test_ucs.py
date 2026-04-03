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
from freecell.solvers.DFS import DFSSolver
from freecell.solvers.UCS import UCSSolver
from freecell.solvers.Astar import AstarSolver

def evaluate_solver(solver_class, solver_name: str, seeds: list[int], max_expansions: int):
    results = {
        "solved": [],
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
        results["solved"].append(res.solved)
        
        mem_mb = res.peak_memory_usage / (1024 * 1024)
        
        if res.solved:
            results["move_counts"].append(res.move_count)
            print(f"SOLVED: \ttime={res.elapsed_seconds:.3f}s \tnodes={res.expanded_nodes} \tmem={mem_mb:.2f}MB \tmoves={res.move_count}")
        else:
            results["move_counts"].append(None)
            print(f"FAILED: \ttime={res.elapsed_seconds:.3f}s \tnodes={res.expanded_nodes} \tmem={mem_mb:.2f}MB (Hit Limit)")
            
    return results


def plot_results(data: dict, seeds: list[int], max_expansions: int):
    alg_name = list(data.keys())[0]
    res = data[alg_name]
    
    times = res["times"]
    expansions = res["expansions"]
    memories = [m / (1024 * 1024) for m in res["memories"]]
    move_counts = res["move_counts"]
    solved = res["solved"]
    
    # Save a CSV dump with per-seed performance
    with open("tests/ucs_evaluation_data.csv", "w", encoding="utf-8") as f:
        f.write("Seed,Solved,SearchTime(s),PeakMemory(MB),ExpandedNodes,SolutionLength(moves)\n")
        for i, s in enumerate(seeds):
            sol = "Yes" if solved[i] else "No"
            mv = move_counts[i] if move_counts[i] is not None else ""
            f.write(f"{s},{sol},{times[i]:.4f},{memories[i]:.2f},{expansions[i]},{mv}\n")
    print(f"[+] Per-seed data saved to 'tests/ucs_evaluation_data.csv' for Word/Latex tables.")

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n[!] matplotlib is not installed. Skipping plot generation.")
        print("[!] To generate plots, run: pip install matplotlib")
        return
    
    # Plot 4 specific metrics across seeds
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"{alg_name} Performance Across Seeds (Max Nodes: {max_expansions})", fontsize=16)
    
    x_seeds = [str(s) for s in seeds]
    
    # 1. Avg Time
    axs[0, 0].plot(x_seeds, times, marker='o', color='#023E8A')
    axs[0, 0].set_title("Search Time per Seed (s)")
    axs[0, 0].set_ylabel("Seconds")
    axs[0, 0].grid(True, linestyle='--', alpha=0.7)

    # 2. Peak Memory
    axs[0, 1].plot(x_seeds, memories, marker='o', color='#0077B6')
    axs[0, 1].set_title("Peak Memory per Seed (MB)")
    axs[0, 1].set_ylabel("Megabytes")
    axs[0, 1].grid(True, linestyle='--', alpha=0.7)

    # 3. Avg Nodes Expanded
    axs[1, 0].plot(x_seeds, expansions, marker='o', color='#0096C7')
    axs[1, 0].set_title("Expanded Nodes per Seed")
    axs[1, 0].set_ylabel("Nodes")
    axs[1, 0].get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    axs[1, 0].grid(True, linestyle='--', alpha=0.7)

    # 4. Avg Solution Length (Path Length)
    solved_seeds = [str(s) for i, s in enumerate(seeds) if solved[i]]
    solved_moves = [m for m in move_counts if m is not None]
    
    if solved_moves:
        axs[1, 1].plot(solved_seeds, solved_moves, marker='o', color='#48CAE4', linestyle='-' if len(solved_moves) > 1 else 'None')
    axs[1, 1].set_title("Solution Length per Seed (Moves)")
    axs[1, 1].set_ylabel("Moves")
    axs[1, 1].grid(True, linestyle='--', alpha=0.7)

    plt.tight_layout()
    output_path = Path("tests/ucs_evaluation_plot.png")
    plt.savefig(output_path, dpi=300)
    print(f"\n[+] Success! Line chart plot saved to '{output_path}'")
    
    # Print overall summary
    solve_rate = sum(solved) / len(seeds) * 100
    print(f"\n--- OVERALL SUMMARY for {alg_name} ---")
    print(f"Solve Rate:      {solve_rate:.1f}%")
    print(f"Avg Time:        {mean(times):.4f} s")
    print(f"Avg Nodes:       {mean(expansions):.1f}")
    if solved_moves:
        print(f"Avg Sol. Length: {mean(solved_moves):.1f} moves")


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
    data["UCS"] = evaluate_solver(UCSSolver, "UCS", seeds, max_expansions)
    
    plot_results(data, seeds, max_expansions)

if __name__ == "__main__":
    main()
