from __future__ import annotations

import sys
import unittest
from collections import deque
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core import Card, GameState
from freecell.solvers.BFS import BFSSolver


def c(short_name: str) -> Card:
    return Card.from_short_name(short_name)


def explore_unique_keys(initial_state, target_expansions: int, key_fn):
    solver = BFSSolver()
    queue: deque = deque([initial_state])
    seen_keys = {key_fn(initial_state)}
    expanded = 0

    started = perf_counter()
    while queue and expanded < target_expansions:
        state = queue.popleft()
        expanded += 1

        for move in solver.iter_legal_moves(state):
            next_state = solver.transition(state, move, validate=False)
            next_key = key_fn(next_state)
            if next_key in seen_keys:
                continue
            seen_keys.add(next_key)
            queue.append(next_state)

    elapsed = perf_counter() - started
    return expanded, len(seen_keys), elapsed


class CanonicalizationTests(unittest.TestCase):
    def test_canonical_key_ignores_freecell_and_cascade_permutations(self) -> None:
        state_a = GameState(
            cascades=(
                (c("8C"), c("7D")),
                (c("6S"),),
                tuple(),
                (c("5H"),),
                tuple(),
                tuple(),
                tuple(),
                tuple(),
            ),
            freecells=(c("AS"), c("2H"), None, None),
            foundations=(1, 0, 0, 0),
        ).to_packed()

        state_b = GameState(
            cascades=(
                (c("5H"),),
                tuple(),
                (c("6S"),),
                tuple(),
                tuple(),
                tuple(),
                tuple(),
                (c("8C"), c("7D")),
            ),
            freecells=(None, c("2H"), None, c("AS")),
            foundations=(1, 0, 0, 0),
        ).to_packed()

        self.assertNotEqual(state_a.key(), state_b.key())
        self.assertEqual(state_a.canonical_key(), state_b.canonical_key())

    def test_canonical_key_never_increases_unique_frontier(self) -> None:
        initial = GameState.initial(seed=1).to_packed()
        target_expansions = 600

        _, raw_unique, _ = explore_unique_keys(
            initial_state=initial,
            target_expansions=target_expansions,
            key_fn=lambda s: s.key(),
        )
        _, canonical_unique, _ = explore_unique_keys(
            initial_state=initial,
            target_expansions=target_expansions,
            key_fn=lambda s: s.canonical_key(),
        )

        self.assertLessEqual(canonical_unique, raw_unique)


if __name__ == "__main__":
    unittest.main()
