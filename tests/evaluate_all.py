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

COLORS = ['#03045E', '#023E8A', '#0077B6', '#0096C7', '#48CAE4']

# ==========================================
# 1. SOLVER EVALUATION
# ==========================================

def evaluate_solver(solver_class, solver_name: str, seeds: list[int], max_expansions: int):
    results = {
        "solved": 0,
        "times": [],
        "expansions": [],
        "memories": [],
        "move_counts": [],
        "statuses": []
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
            results["statuses"].append("Solved")
            print(f"SOLVED: \ttime={res.elapsed_seconds:.3f}s \tnodes={res.expanded_nodes} \tmem={mem_mb:.2f}MB \tmoves={res.move_count}")
        elif res.expanded_nodes >= max_expansions:
            results["move_counts"].append(None)
            results["statuses"].append("Hit Limit")
            print(f"FAILED: \ttime={res.elapsed_seconds:.3f}s \tnodes={res.expanded_nodes} \tmem={mem_mb:.2f}MB (Hit Limit)")
        else:
            results["move_counts"].append(None)
            results["statuses"].append("OOM/Timeout")
            print(f"FAILED: \ttime={res.elapsed_seconds:.3f}s \tnodes={res.expanded_nodes} \tmem={mem_mb:.2f}MB (OOM/Timeout/Exhausted)")
            
    return results

# ==========================================
# 2. DATA EXPORT
# ==========================================

def save_csv_report(data: dict, seeds: list[int]):
    solvers = list(data.keys())
    solve_rates = [(data[s]["solved"] / len(seeds)) * 100 for s in solvers]
    avg_times = [mean(data[s]["times"]) for s in solvers]
    avg_nodes = [mean(data[s]["expansions"]) for s in solvers]
    avg_memories = [mean(data[s]["memories"]) / (1024 * 1024) for s in solvers] # MB
    
    avg_moves = []
    for s in solvers:
        valid_moves = [m for m in data[s]["move_counts"] if m is not None]
        if len(valid_moves) > 0:
            avg_moves.append(mean(valid_moves))
        else:
            avg_moves.append(0.0)

    csv_path = Path("tests/evaluation_data.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Algorithm,SolveRate(%),AvgSearchTime(s),AvgPeakMemory(MB),AvgExpandedNodes,AvgSolutionLength(moves)\n")
        for i, s in enumerate(solvers):
            f.write(f"{s},{solve_rates[i]:.1f},{avg_times[i]:.4f},{avg_memories[i]:.2f},{avg_nodes[i]:.1f},{avg_moves[i]:.1f}\n")
    print(f"\n[+] Raw summary data saved to '{csv_path}' for Word/Latex tables.")


# ==========================================
# 3. PLOTTING FUNCTIONS
# ==========================================

def plot_solve_rate_chart(data: dict, seeds: list[int]):
    import matplotlib.pyplot as plt
    solvers = list(data.keys())
    solve_rates = [(data[s]["solved"] / len(seeds)) * 100 for s in solvers]

    plt.figure(figsize=(6, 5))
    bar_colors = COLORS[:len(solvers)] if len(solvers) <= len(COLORS) else None
    plt.bar(solvers, solve_rates, color=bar_colors)
    plt.title(f"Algorithm Success Rate ({len(seeds)} Seeds)", fontsize=14)
    plt.ylabel("Success Rate (%)")
    plt.ylim(0, 105)
    for i, v in enumerate(solve_rates):
        plt.text(i, v + 2, f"{v:.1f}%", ha='center', fontweight='bold', fontsize=12)
    
    plt.tight_layout()
    out_path = Path("tests/solve_rate_plot.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[+] Solve rate chart saved to '{out_path}'")


def plot_average_bar_charts(data: dict, seeds: list[int], max_expansions: int):
    import matplotlib.pyplot as plt

    solvers = list(data.keys())
    avg_times = [mean(data[s]["times"]) for s in solvers]
    avg_nodes = [mean(data[s]["expansions"]) for s in solvers]
    avg_memories = [mean(data[s]["memories"]) / (1024 * 1024) for s in solvers]
    
    avg_moves = []
    for s in solvers:
        valid_moves = [m for m in data[s]["move_counts"] if m is not None]
        if len(valid_moves) > 0:
            avg_moves.append(mean(valid_moves))
        else:
            avg_moves.append(0)

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Algorithm Comparison ({len(seeds)} Seeds | Max Nodes: {max_expansions})", fontsize=16)
    
    bar_colors = COLORS[:len(solvers)] if len(solvers) <= len(COLORS) else None

    # 1. Avg Time
    axs[0, 0].bar(solvers, avg_times, color=bar_colors)
    axs[0, 0].set_title("Average Search Time (s)")
    axs[0, 0].set_ylabel("Seconds")
    for i, v in enumerate(avg_times):
        axs[0, 0].text(i, v + (max(avg_times)*0.02), f"{v:.3f}s", ha='center', fontweight='bold')

    # 2. Peak Memory
    axs[0, 1].bar(solvers, avg_memories, color=bar_colors)
    axs[0, 1].set_title("Average Peak Memory (MB)")
    axs[0, 1].set_ylabel("Megabytes")
    for i, v in enumerate(avg_memories):
        axs[0, 1].text(i, v + (max(avg_memories)*0.02), f"{v:.2f} MB", ha='center', fontweight='bold')

    # 3. Avg Nodes Expanded
    axs[1, 0].bar(solvers, avg_nodes, color=bar_colors)
    axs[1, 0].set_title("Average Expanded Nodes")
    axs[1, 0].set_ylabel("Nodes")
    axs[1, 0].get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    for i, v in enumerate(avg_nodes):
        axs[1, 0].text(i, v + (max(avg_nodes)*0.02), f"{v:,.0f}", ha='center', fontweight='bold')

    # 4. Avg Solution Length
    axs[1, 1].bar(solvers, avg_moves, color=bar_colors)
    axs[1, 1].set_title("Average Solution Length (Moves)")
    axs[1, 1].set_ylabel("Moves")
    for i, v in enumerate(avg_moves):
        msg = f"{v:.1f}" if v > 0 else "N/A"
        axs[1, 1].text(i, v + (max(avg_moves+[1])*0.02), msg, ha='center', fontweight='bold')

    plt.tight_layout()
    output_path = Path("tests/evaluation_plot.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"[+] Average Comparative plot saved to '{output_path}'")


def plot_scatter_for_algorithm(alg_name: str, alg_data: dict):
    import matplotlib.pyplot as plt
    
    valid_moves = []
    valid_nodes = []
    
    for moves, nodes in zip(alg_data["move_counts"], alg_data["expansions"]):
        if moves is not None:
            valid_moves.append(moves)
            valid_nodes.append(nodes)
            
    fig, ax = plt.subplots(figsize=(6, 5))
    if valid_moves:
        ax.scatter(valid_moves, valid_nodes, color='#1f77b4', edgecolors='black', alpha=0.7)
        ax.set_xlabel('Solution Length (Moves)')
        ax.set_ylabel('Expanded Nodes')
        ax.set_yscale('log') # Add log scale to scatter nodes for better variation visually
        ax.set_title(f'{alg_name}: Solution Length vs Expanded Nodes (Log)')
        ax.grid(True, linestyle='--', alpha=0.5)
    else:
        ax.text(0.5, 0.5, f"No solutions found for {alg_name}", ha='center', va='center', fontsize=12)
        ax.set_title(f'{alg_name}: Solution Length vs Expanded Nodes')
        
    plt.tight_layout()
    safe_name = alg_name.replace("*", "star")
    out_path = Path(f"tests/{safe_name}_scatter.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[+] Scatter plot for {alg_name} saved to '{out_path}'")


def plot_boxplots_per_algorithm(alg_name: str, alg_data: dict):
    """VER 1: 1 algorithm -> 1 image (containing 4 metric subplots)"""
    import matplotlib.pyplot as plt
    
    times = alg_data["times"]
    memories = [m / (1024 * 1024) for m in alg_data["memories"]]
    expansions = alg_data["expansions"]
    valid_moves = [m for m in alg_data["move_counts"] if m is not None]

    fig, axs = plt.subplots(2, 2, figsize=(10, 8))
    fig.suptitle(f"{alg_name} Performance Distributions", fontsize=16)
    
    def customized_boxplot(ax, data_array, color, y_label, title, use_log):
        if not data_array:
            ax.text(0.5, 0.5, "No data (0 solutions)", ha='center', va='center')
            ax.set_title(title)
            return
        bp = ax.boxplot(data_array, patch_artist=True)
        for box in bp['boxes']: box.set_facecolor(color)
        if use_log:
            ax.set_yscale('log')
        ax.set_title(title + (" (Log)" if use_log else ""))
        ax.set_ylabel(y_label)
        ax.grid(True, linestyle='--', alpha=0.5)

    customized_boxplot(axs[0, 0], times, '#00b4d8', "Seconds", "Search Time", use_log=True)
    customized_boxplot(axs[0, 1], memories, '#0096c7', "MB", "Peak Memory", use_log=True)
    customized_boxplot(axs[1, 0], expansions, '#0077b6', "Nodes", "Expanded Nodes", use_log=True)
    customized_boxplot(axs[1, 1], valid_moves, '#023e8a', "Moves", "Solution Length", use_log=False)

    plt.tight_layout()
    safe_name = alg_name.replace("*", "star")
    out_path = Path(f"tests/{safe_name}_boxplots.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[+] Algo Boxplots for {alg_name} saved to '{out_path}'")


def _draw_metric_boxplot(metric_name, data_lists, labels, use_log, y_label, color, filename):
    import matplotlib.pyplot as plt
    if not data_lists:
        return
        
    fig, ax = plt.subplots(figsize=(8, 6))
    bp = ax.boxplot(data_lists, labels=labels, patch_artist=True)
    for box in bp['boxes']: box.set_facecolor(color)
    if use_log:
        ax.set_yscale('log')
    ax.set_title(f"Algorithm Comparison: {metric_name}" + (" (Log Scale)" if use_log else ""))
    ax.set_ylabel(y_label)
    ax.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(Path(f"tests/{filename}"), dpi=300)
    plt.close()
    print(f"[+] Metric Boxplot saved to 'tests/{filename}'")

def plot_boxplots_per_metric(data: dict):
    """VER 2: 1 metric -> 1 image (containing all algorithms side-by-side)"""
    algos = list(data.keys())
    
    # 1. Search Time
    times = [data[a]["times"] for a in algos]
    _draw_metric_boxplot("Search Time", times, algos, True, "Seconds", "#00b4d8", "boxplot_metric_search_time.png")
    
    # 2. Expanded Nodes
    expansions = [data[a]["expansions"] for a in algos]
    _draw_metric_boxplot("Expanded Nodes", expansions, algos, True, "Nodes", "#0096c7", "boxplot_metric_expanded_nodes.png")
    
    # 3. Peak Memory
    memories = [[m / (1024*1024) for m in data[a]["memories"]] for a in algos]
    _draw_metric_boxplot("Peak Memory", memories, algos, True, "MB", "#0077b6", "boxplot_metric_peak_memory.png")
    
    # 4. Solution Length
    moves_data = []
    moves_labels = []
    for a in algos:
        valid = [m for m in data[a]["move_counts"] if m is not None]
        if valid:
            moves_data.append(valid)
            moves_labels.append(a)
    if moves_data:
        _draw_metric_boxplot("Solution Length", moves_data, moves_labels, False, "Moves", "#023e8a", "boxplot_metric_solution_length.png")


# ==========================================
# 4. MAIN ORCHESTRATION
# ==========================================

def execute_chart_generation(data: dict, seeds: list[int], max_expansions: int):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n[!] matplotlib is not installed. Skipping plot generation.")
        print("[!] To generate plots, run: pip install matplotlib")
        return
        
    print("\n--- Generating Plots ---")
    
    # 1. Average Bar Charts (The Original 4 pane)
    plot_average_bar_charts(data, seeds, max_expansions)
    
    # 2. Blueprint Solve Rate Chart (The Original blue 1 pane)
    plot_solve_rate_chart(data, seeds)
    
    # 3. Scatter Plots & Algorithm Boxplots (1 output per algo)
    for alg_name, alg_data in data.items():
        plot_scatter_for_algorithm(alg_name, alg_data)
        plot_boxplots_per_algorithm(alg_name, alg_data)
        
    # 4. Metric Boxplots (1 output per metric across algorithms)
    plot_boxplots_per_metric(data)


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
    data["DFS"] = evaluate_solver(DFSSolver, "DFS", seeds, max_expansions)
    data["UCS"] = evaluate_solver(UCSSolver, "UCS", seeds, max_expansions)
    data["A*"] = evaluate_solver(lambda: AstarSolver(), "A*", seeds, max_expansions)
    
    save_csv_report(data, seeds)
    execute_chart_generation(data, seeds, max_expansions)

if __name__ == "__main__":
    main()
