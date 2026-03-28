import sys
from pathlib import Path

# Add the 'src' directory to sys.path so 'freecell' can be imported
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path.resolve()))

from freecell.GUI.app import run


if __name__ == "__main__":
    run()
