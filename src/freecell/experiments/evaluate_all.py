import sys
import os
from pathlib import Path
from statistics import mean
from joblib import Parallel, delayed

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
from freecell.core.rules import is_descending_alternating_codes

COLORS = ['#03045E', '#023E8A', '#0077B6', '#0096C7', '#48CAE4']


# ==========================================
# 0. CONFIGURATION (edit directly)
# ==========================================
START_SEED = 1
SEED_COUNT = 50
MAX_EXPANSIONS = 100_000
N_JOBS = -1


def h_cards_remaining(state):
    return float(state.cards_remaining())


def h_occupied_freecells(state):
    empty_freecells = state.freecell_count_empty()
    return float(state.freecell_slot_count - empty_freecells)


def h_disorder(state):
    total_disorder = 0
    for c_idx in range(state.cascade_count):
        length = state.cascade_length(c_idx)
        if length <= 1:
            continue
        cards = state.cascade_tail_codes(c_idx, length)
        for i in range(length - 1):
            if not is_descending_alternating_codes(cards[i : i + 2]):
                total_disorder += (length - i - 1)
                break
    return float(total_disorder)

# ==========================================
# 1. SOLVER EVALUATION
# ==========================================

def _evaluate_seed(solver_factory, seed: int, max_expansions: int) -> dict:
    init = GameState(deal_cascades(seed)).to_packed()
    solver = solver_factory()
    if hasattr(solver, "max_expansions"):
        solver.max_expansions = max_expansions

    # Disable tracemalloc in batch runs to reduce overhead.
    res = solver.timed_solve(init, trace_peak_memory=False)

    mem_mb = res.peak_memory_usage / (1024 * 1024)
    if res.solved:
        status = "Solved"
        move_count = res.move_count
    elif res.expanded_nodes >= max_expansions:
        status = "Hit Limit"
        move_count = None
    else:
        status = "OOM/Timeout"
        move_count = None

    return {
        "seed": seed,
        "elapsed_seconds": res.elapsed_seconds,
        "expanded_nodes": res.expanded_nodes,
        "peak_memory_usage": res.peak_memory_usage,
        "mem_mb": mem_mb,
        "solved": res.solved,
        "move_count": move_count,
        "status": status,
    }


def evaluate_solver(solver_factory, solver_name: str, seeds: list[int], max_expansions: int):
    results = {
        "solved": 0,
        "times": [],
        "expansions": [],
        "memories": [],
        "move_counts": [],
        "statuses": []
    }
    print(f"\n[{solver_name}] Testing {len(seeds)} problems (Limits: {max_expansions} expansions)")

    rows = Parallel(n_jobs=N_JOBS, backend="loky")(
        delayed(_evaluate_seed)(solver_factory, s, max_expansions) for s in seeds
    )

    for row in sorted(rows, key=lambda r: r["seed"]):
        s = row["seed"]
        print(f"  -> seed={s:02d} | ", end="", flush=True)

        results["times"].append(row["elapsed_seconds"])
        results["expansions"].append(row["expanded_nodes"])
        results["memories"].append(row["peak_memory_usage"])
        results["statuses"].append(row["status"])

        if row["solved"]:
            results["solved"] += 1
            results["move_counts"].append(row["move_count"])
            print(
                f"SOLVED: \ttime={row['elapsed_seconds']:.3f}s \tnodes={row['expanded_nodes']} "
                f"\tmem={row['mem_mb']:.2f}MB \tmoves={row['move_count']}"
            )
        elif row["status"] == "Hit Limit":
            results["move_counts"].append(None)
            print(
                f"FAILED: \ttime={row['elapsed_seconds']:.3f}s \tnodes={row['expanded_nodes']} "
                f"\tmem={row['mem_mb']:.2f}MB (Hit Limit)"
            )
        else:
            results["move_counts"].append(None)
            print(
                f"FAILED: \ttime={row['elapsed_seconds']:.3f}s \tnodes={row['expanded_nodes']} "
                f"\tmem={row['mem_mb']:.2f}MB (OOM/Timeout/Exhausted)"
            )
            
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

def _draw_scatter(x_data, y_data, x_label, y_label, title, out_path, use_log_x=False, draw_trendline=False):
    if not x_data or not y_data:
        return
        
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(x_data, y_data, color='#1f77b4', edgecolors='black', alpha=0.7)
    
    if draw_trendline and len(x_data) > 1 and np is not None:
        try:
            x_arr = np.array(x_data)
            y_arr = np.array(y_data)
            if use_log_x:
                valid = x_arr > 0
                x_arr = x_arr[valid]
                y_arr = y_arr[valid]
                if len(x_arr) > 1:
                    # Check if x_arr has at least 2 distinct values to avoid Singular Matrix / polyfit hang
                    if len(np.unique(x_arr)) > 1:
                        x_fit = np.log10(x_arr)
                        z = np.polyfit(x_fit, y_arr, 1)
                        p = np.poly1d(z)
                        
                        # Generate points for the line
                        x_seq = np.logspace(np.log10(min(x_arr)), np.log10(max(x_arr)), 100)
                        ax.plot(x_seq, p(np.log10(x_seq)), "r--", linewidth=2, label="Trendline")
                        ax.legend()
                    else:
                        print(f"  [i] Bỏ qua Trendline cho {title} vì mọi điểm X đều trùng nhau.")
            else:
                if len(np.unique(x_arr)) > 1:
                    z = np.polyfit(x_arr, y_arr, 1)
                    p = np.poly1d(z)
                    x_seq = np.linspace(min(x_arr), max(x_arr), 100)
                    ax.plot(x_seq, p(x_seq), "r--", linewidth=2, label="Trendline")
                    ax.legend()
                else:
                    print(f"  [i] Bỏ qua Trendline cho {title} vì mọi điểm X đều trùng nhau.")
        except Exception as e:
            print(f"  [!] Could not draw trendline for {title}: {e}")
            
    if use_log_x:
        ax.set_xscale('log')
        
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[+] Scatter plot saved to '{out_path}'")


def plot_solve_rate_chart(data: dict, seeds: list[int]):
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
    from pathlib import Path
    
    valid_moves = []
    valid_nodes = []
    
    for moves, nodes in zip(alg_data["move_counts"], alg_data["expansions"]):
        if moves is not None:
            valid_moves.append(moves)
            valid_nodes.append(nodes)
            
    safe_name = alg_name.replace("*", "star")
    
    # 1. Original Scatter: Solution Length vs Nodes
    fig, ax = plt.subplots(figsize=(6, 5))
    if valid_moves:
        ax.scatter(valid_moves, valid_nodes, color='#1f77b4', edgecolors='black', alpha=0.7)
        ax.set_xlabel('Solution Length (Moves)')
        ax.set_ylabel('Expanded Nodes')
        ax.set_yscale('log')
        ax.set_title(f'{alg_name}: Solution Length vs Expanded Nodes (Log Y)')
        ax.grid(True, linestyle='--', alpha=0.5)
    else:
        ax.text(0.5, 0.5, f"No solutions found for {alg_name}", ha='center', va='center', fontsize=12)
        ax.set_title(f'{alg_name}: Solution Length vs Expanded Nodes')
        
    plt.tight_layout()
    out_path = Path(f"tests/{safe_name}_scatter.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[+] Original scatter plot for {alg_name} saved to '{out_path}'")

    # Correlation Scatters using all data runs
    all_nodes = alg_data["expansions"]
    all_times = alg_data["times"]
    all_memories = [m / (1024 * 1024) for m in alg_data["memories"]]
    
    # 2. X: Nodes(log), Y: Time (No Trend)
    _draw_scatter(
        all_nodes, all_times, 'Expanded Nodes (Log X)', 'Search Time (s)', 
        f'{alg_name}: Nodes vs Search Time', Path(f"tests/{safe_name}_nodes_time_scatter.png"), 
        use_log_x=True, draw_trendline=False
    )
    
    # 3. X: Nodes(log), Y: Time (With Trend)
    _draw_scatter(
        all_nodes, all_times, 'Expanded Nodes (Log X)', 'Search Time (s)', 
        f'{alg_name}: Nodes vs Search Time (Trend)', Path(f"tests/{safe_name}_nodes_time_scatter_trend.png"), 
        use_log_x=True, draw_trendline=True
    )
    
    # 4. X: Nodes(log), Y: Memory (No Trend)
    _draw_scatter(
        all_nodes, all_memories, 'Expanded Nodes (Log X)', 'Peak Memory (MB)', 
        f'{alg_name}: Nodes vs Peak Memory', Path(f"tests/{safe_name}_nodes_memory_scatter.png"), 
        use_log_x=True, draw_trendline=False
    )
    
    # 5. X: Nodes(log), Y: Memory (With Trend)
    _draw_scatter(
        all_nodes, all_memories, 'Expanded Nodes (Log X)', 'Peak Memory (MB)', 
        f'{alg_name}: Nodes vs Peak Memory (Trend)', Path(f"tests/{safe_name}_nodes_memory_scatter_trend.png"), 
        use_log_x=True, draw_trendline=True
    )


def plot_boxplots_per_algorithm(alg_name: str, alg_data: dict):
    """VER 1: 1 algorithm -> 1 image (containing 4 metric subplots)"""
    
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

def print_summary_tables(data: dict):
    rows = []
    for alg, alg_data in data.items():
        for i in range(len(alg_data["times"])):
            rows.append({
                "Algorithm": alg,
                "Solved": alg_data["statuses"][i] == "Solved",
                "Nodes": alg_data["expansions"][i],
                "Time (s)": alg_data["times"][i],
                "Memory (MB)": alg_data["memories"][i] / (1024 * 1024),
                "Moves": alg_data["move_counts"][i] if alg_data["move_counts"][i] is not None else pd.NA,
                "True_Cost": alg_data["move_counts"][i] if alg_data["move_counts"][i] is not None else pd.NA
            })
            
    df = pd.DataFrame(rows)
    
    output_lines = []
    
    # --- Bảng 1 ---
    output_lines.append("="*110)
    output_lines.append(" Bảng 1: Hiệu suất và Tiêu thụ tài nguyên (Efficiency & Resource Usage)")
    output_lines.append("="*110)
    
    table1_rows = []
    for alg in df['Algorithm'].unique():
        g = df[df['Algorithm'] == alg]
        table1_rows.append({
            'Algorithm': alg,
            'Success Rate': f"{(g['Solved'].mean() * 100):.1f}%",
            'Avg. Expanded Nodes': round(g['Nodes'].mean(), 1),
            'Max Expanded Nodes': g['Nodes'].max(),
            'Avg. Time (s)': round(g['Time (s)'].mean(), 4),
            'Avg. Peak Memory (MB)': round(g['Memory (MB)'].mean(), 2),
            'Max Peak Memory (MB)': round(g['Memory (MB)'].max(), 2),
        })
    table1_df = pd.DataFrame(table1_rows).set_index('Algorithm')
    output_lines.append(table1_df.to_string())
    output_lines.append("")
    
    # --- Bảng 2 ---
    output_lines.append("="*110)
    output_lines.append(" Bảng 2: Chất lượng Lời giải (Solution Quality) - Chỉ tính ca Solved")
    output_lines.append("="*110)
    
    table2_rows = []
    for alg in df['Algorithm'].unique():
        g = df[df['Algorithm'] == alg]
        total = len(g)
        solved = g['Solved'].sum()
        if solved == 0:
            table2_rows.append({
                'Algorithm': alg,
                'Solved Cases': f"{solved}/{total}",
                'Min Moves': "N/A", 'Avg. Moves': "N/A", 'Max Moves': "N/A",
                'Avg. True Cost': "N/A", 'Max True Cost': "N/A"
            })
        else:
            sol = g[g['Solved']]
            table2_rows.append({
                'Algorithm': alg,
                'Solved Cases': f"{solved}/{total}",
                'Min Moves': int(sol['Moves'].min()),
                'Avg. Moves': round(sol['Moves'].mean(), 1),
                'Max Moves': int(sol['Moves'].max()),
                'Avg. True Cost': round(sol['True_Cost'].mean(), 1),
                'Max True Cost': int(sol['True_Cost'].max())
            })
    table2_df = pd.DataFrame(table2_rows).set_index('Algorithm')
    output_lines.append(table2_df.to_string())
    output_lines.append("="*110 + "\n")
    
    # Output to console and save to text file
    final_output = "\n".join(output_lines)
    print(f"\n{final_output}")
    
    out_path = Path("tests/summary_tables.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(final_output)
    print(f"[+] Summary tables saved to '{out_path}' for easy copy-pasting.")


def execute_chart_generation(data: dict, seeds: list[int], max_expansions: int):
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
    seeds = list(range(START_SEED, START_SEED + SEED_COUNT))
    max_expansions = MAX_EXPANSIONS
    
    print("=" * 60)
    print(" FREECELL SOLVER MASS BENCHMARK SUITE")
    print("=" * 60)
    print(f"Config: start_seed={START_SEED}, seed_count={SEED_COUNT}, max_expansions={MAX_EXPANSIONS}, n_jobs={N_JOBS}")
    
    data = {}
    data["BFS"] = evaluate_solver(BFSSolver, "BFS", seeds, max_expansions)
    # data["IDS"] = evaluate_solver(IDSSolver, "IDS", seeds, max_expansions)
    data["DFS"] = evaluate_solver(DFSSolver, "DFS", seeds, max_expansions)
    data["UCS"] = evaluate_solver(UCSSolver, "UCS", seeds, max_expansions)
    data["A*"] = evaluate_solver(
        lambda: AstarSolver(
            heuristics=[
                (h_cards_remaining, 1.0),
                (h_occupied_freecells, 1.0),
                (h_disorder, 1.0),
            ],
            heuristic_weight=2.0,
        ),
        "A*",
        seeds,
        max_expansions,
    )
    
    save_csv_report(data, seeds)
    print_summary_tables(data)
    execute_chart_generation(data, seeds, max_expansions)

if __name__ == "__main__":
    main()
