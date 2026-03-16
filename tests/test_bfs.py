from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from freecell.core import *
from freecell.solvers.BFS import BFSSolver

def main():
    cascades = deal_cascades(1)
    init = GameState(cascades)
    init = init.to_packed()
    solver = BFSSolver()
    result = solver.solve(init)
    print(result)

main()