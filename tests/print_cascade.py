from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SUIT_SYMBOLS: dict[str, str] = {
    "C": "♣",
    "D": "♦",
    "H": "♥",
    "S": "♠",
}
RED_SUITS = {"D", "H"}
ANSI_RED = "\033[31m"
ANSI_RESET = "\033[0m"


def parse_deal_file(path: Path) -> list[list[str]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"Deal file is empty: {path}")

    if lines[0].lower().startswith("deal number:"):
        lines = lines[1:]

    cascades = [line.split() for line in lines]
    if len(cascades) != 8:
        raise ValueError(f"Expected 8 cascades, found {len(cascades)} in {path}")
    return cascades


def seed_cascades(seed: int) -> list[list[str]]:
    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from freecell.core.deal_generator import deal_cascades  # pylint: disable=import-outside-toplevel

    return [[card.short_name for card in cascade] for cascade in deal_cascades(seed=seed)]


def parse_card(token: str) -> tuple[str, str]:
    text = token.strip().upper()
    if len(text) < 2:
        raise ValueError(f"Invalid card token: {token!r}")

    rank = text[:-1]
    suit = text[-1]
    if suit not in SUIT_SYMBOLS:
        raise ValueError(f"Invalid card suit in token: {token!r}")
    return rank, suit


def card_to_display(token: str, color: bool = False) -> str:
    rank, suit = parse_card(token)
    plain = f"{rank}{SUIT_SYMBOLS[suit]}"
    if color and suit in RED_SUITS:
        return f"{ANSI_RED}{plain}{ANSI_RESET}"
    return plain


def should_use_color(color_arg: bool | None) -> bool:
    if color_arg is not None:
        return color_arg
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def print_cascades(cascades: list[list[str]], color: bool = False) -> None:
    max_height = max(len(cascade) for cascade in cascades)
    cell_width = 3

    for row in range(max_height):
        plain_cells: list[str] = []
        rendered_cells: list[str] = []

        for cascade in cascades:
            if row < len(cascade):
                rank, suit = parse_card(cascade[row])
                plain = f"{rank}{SUIT_SYMBOLS[suit]}"
                plain_cells.append(plain)
                rendered_cells.append(card_to_display(cascade[row], color=color))
            else:
                plain_cells.append("")
                rendered_cells.append("")

        padded: list[str] = []
        for plain, rendered in zip(plain_cells, rendered_cells):
            spaces = " " * max(cell_width - len(plain), 0)
            padded.append(f"{rendered}{spaces}")

        print("  ".join(padded).rstrip())


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print FreeCell cascades in a grid format.")
    parser.add_argument(
        "--seed",
        type=int,
        nargs="+",
        required=True,
        help="One or more Microsoft FreeCell deal numbers",
    )

    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument("--color", action="store_true", help="Force ANSI color output")
    color_group.add_argument("--no-color", action="store_true", help="Disable color output")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    color = should_use_color(True if args.color else False if args.no_color else None)
    for index, seed in enumerate(args.seed):
        if len(args.seed) > 1:
            if index > 0:
                print()
            print(f"Seed {seed}:")
        cascades = seed_cascades(seed)
        print_cascades(cascades, color=color)


if __name__ == "__main__":
    main()
