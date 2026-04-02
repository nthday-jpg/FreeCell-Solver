from __future__ import annotations

import csv
import importlib
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
	sys.path.insert(0, str(SRC_DIR))

from freecell.core.state import GameState
from freecell.solvers.Astar import AstarSolver
import matplotlib.pyplot as plt

START_SEED = 1
END_SEED = 500
MAX_EXPANSIONS = 500_000
SAVE_PLOT_PATH: str | None = "/kaggle/working/astar.png"
SAVE_CSV_PATH: str | None = None

def run() -> None:
	solver = AstarSolver(max_expansions=MAX_EXPANSIONS)
	move_counts: list[int] = []
	solved_expansion_counts: list[int] = []
	rows: list[dict[str, str | int]] = []

	total = END_SEED - START_SEED + 1
	solved_count = 0
	unsolved_count = 0
	exception_count = 0

	for seed in range(START_SEED, END_SEED + 1):
		try:
			initial_state = GameState.initial(seed=seed).to_packed()
			result = solver.solve(initial_state)
			if result.solved:
				solved_count += 1
				move_counts.append(result.move_count)
				solved_expansion_counts.append(result.expanded_nodes)
				rows.append(
					{
						"seed": seed,
						"status": "solved",
						"move_count": result.move_count,
						"expanded_nodes": result.expanded_nodes,
						"error": "",
					}
				)
				print(f"seed={seed:>4} solved moves={result.move_count:>4} expanded={result.expanded_nodes}")
			else:
				unsolved_count += 1
				rows.append(
					{
						"seed": seed,
						"status": "unsolved",
						"move_count": "",
						"expanded_nodes": result.expanded_nodes,
						"error": "",
					}
				)
				print(f"seed={seed:>4} unsolved expanded={result.expanded_nodes}")
		except Exception as exc:
			exception_count += 1
			rows.append(
				{
					"seed": seed,
					"status": "error",
					"move_count": "",
					"expanded_nodes": "",
					"error": f"{type(exc).__name__}: {exc}",
				}
			)
			print(f"seed={seed:>4} error={type(exc).__name__}: {exc}")

	failure_count = unsolved_count + exception_count

	print("\nSummary")
	print(f"total_seeds={total}")
	print(f"solved={solved_count}")
	print(f"unsolved={unsolved_count}")
	print(f"exceptions={exception_count}")
	print(f"failures={failure_count}")

	fig_hist, ax_moves = plt.subplots(1, 1, figsize=(8, 5))
	if move_counts:
		move_bins = max(1, min(20, len(set(move_counts))))
		ax_moves.hist(move_counts, bins=move_bins, edgecolor="black", alpha=0.8)
	ax_moves.set_title("A* Move Count Distribution")
	ax_moves.set_xlabel("Move count (solved seeds)")
	ax_moves.set_ylabel("Frequency")
	ax_moves.grid(True, alpha=0.3)

	fig_xy, ax_xy = plt.subplots(1, 1, figsize=(8, 5))
	if move_counts and solved_expansion_counts:
		ax_xy.scatter(move_counts, solved_expansion_counts, alpha=0.85)
	ax_xy.set_title("A* Expanded Nodes vs Move Count")
	ax_xy.set_xlabel("Move count")
	ax_xy.set_ylabel("Expanded nodes")
	ax_xy.grid(True, alpha=0.3)

	# Keep summary visible on the plot for quick experiment screenshots.
	summary_text = (
		f"total={total}  solved={solved_count}  "
		f"unsolved={unsolved_count}  exceptions={exception_count}  failures={failure_count}"
	)
	fig_hist.text(0.01, 0.01, summary_text, ha="left", va="bottom", fontsize=9)
	fig_hist.tight_layout(rect=(0, 0.04, 1, 1))
	fig_xy.text(0.01, 0.01, summary_text, ha="left", va="bottom", fontsize=9)
	fig_xy.tight_layout(rect=(0, 0.04, 1, 1))

	if SAVE_PLOT_PATH:
		save_path = Path(SAVE_PLOT_PATH)
		save_path.parent.mkdir(parents=True, exist_ok=True)
		hist_path = save_path.with_name(f"{save_path.stem}_hist{save_path.suffix}")
		xy_path = save_path.with_name(f"{save_path.stem}_xy{save_path.suffix}")
		fig_hist.savefig(hist_path, dpi=150)
		fig_xy.savefig(xy_path, dpi=150)
		print(f"saved_plot={hist_path}")
		print(f"saved_plot={xy_path}")

	csv_path: Path | None = None
	if SAVE_CSV_PATH:
		csv_path = Path(SAVE_CSV_PATH)
	elif SAVE_PLOT_PATH:
		save_path = Path(SAVE_PLOT_PATH)
		csv_path = save_path.with_name(f"{save_path.stem}_results.csv")

	if csv_path is not None:
		csv_path.parent.mkdir(parents=True, exist_ok=True)
		with csv_path.open("w", newline="", encoding="utf-8") as f:
			writer = csv.DictWriter(
				f,
				fieldnames=["seed", "status", "move_count", "expanded_nodes", "error"],
			)
			writer.writeheader()
			writer.writerows(rows)
		print(f"saved_csv={csv_path}")

	plt.show()
if __name__ == "__main__":
	run()
