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

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n[!] matplotlib is not installed. Skipping plot generation.")
        print("[!] To generate plots, run: pip install matplotlib")
        return
    


    # We plot 4 specific metrics requested: Time, Memory, Expanded Nodes, Search Length
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Algorithm Comparison ({len(seeds)} Seeds | Max Nodes: {max_expansions})", fontsize=16)
    
    colors = ['#c23b22', '#f39c12', '#2ecc71']

    # 1. Avg Time
    axs[0, 0].bar(solvers, avg_times, color=colors)
    axs[0, 0].set_title("Average Search Time (s)")
    axs[0, 0].set_ylabel("Seconds")
    for i, v in enumerate(avg_times):
        axs[0, 0].text(i, v + (max(avg_times)*0.02), f"{v:.3f}s", ha='center', fontweight='bold')

    # 2. Peak Memory
    axs[0, 1].bar(solvers, avg_memories, color=colors)
    axs[0, 1].set_title("Average Peak Memory (MB)")
    axs[0, 1].set_ylabel("Megabytes")
    for i, v in enumerate(avg_memories):
        axs[0, 1].text(i, v + (max(avg_memories)*0.02), f"{v:.2f} MB", ha='center', fontweight='bold')

    # 3. Avg Nodes Expanded
    axs[1, 0].bar(solvers, avg_nodes, color=colors)
    axs[1, 0].set_title("Average Expanded Nodes")
    axs[1, 0].set_ylabel("Nodes")
    axs[1, 0].get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    for i, v in enumerate(avg_nodes):
        axs[1, 0].text(i, v + (max(avg_nodes)*0.02), f"{v:,.0f}", ha='center', fontweight='bold')

    # 4. Avg Search Length (Path Length)
    axs[1, 1].bar(solvers, avg_moves, color=colors)
    axs[1, 1].set_title("Average Search Length (Moves)")
    axs[1, 1].set_ylabel("Moves")
    for i, v in enumerate(avg_moves):
        msg = f"{v:.1f}" if v > 0 else "N/A"
        axs[1, 1].text(i, v + (max(avg_moves+[1])*0.02), msg, ha='center', fontweight='bold')

    plt.tight_layout()
    output_path = Path("tests/evaluation_plot.png")
    plt.savefig(output_path, dpi=300)
    print(f"\n[+] Success! Comparative plot saved to '{output_path}'")

    # 5. Separate Solve Rate Plot
    plt.figure(figsize=(6, 5))
    plt.bar(solvers, solve_rates, color=colors)
    plt.title(f"Algorithm Success Rate ({len(seeds)} Seeds)", fontsize=14)
    plt.ylabel("Success Rate (%)")
    plt.ylim(0, 105)
    for i, v in enumerate(solve_rates):
        plt.text(i, v + 2, f"{v:.1f}%", ha='center', fontweight='bold', fontsize=12)
    
    plt.tight_layout()
    solve_rate_path = Path("tests/solve_rate_plot.png")
    plt.savefig(solve_rate_path, dpi=300)
    print(f"[+] Success! Separate Solve Rate plot saved to '{solve_rate_path}'")


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
    data["BFS"] = evaluate_solver(BFSSolver, "BFS", seeds, max_expansions)
    data["IDS"] = evaluate_solver(IDSSolver, "IDS", seeds, max_expansions)
    data["UCS"] = evaluate_solver(UCSSolver, "UCS", seeds, max_expansions)
    data["A*"] = evaluate_solver(AstarSolver, "A*", seeds, max_expansions)
    
    plot_results(data, seeds, max_expansions)

if __name__ == "__main__":
    main()
