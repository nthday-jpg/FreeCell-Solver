from __future__ import annotations

import sys
import tracemalloc
from collections import deque
from collections.abc import Hashable
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import TypeVar

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freecell.core import (
    Card,
    GameState,
    PackedState,
    can_move_to_foundation,
    can_stack_on_cascade,
    card_to_code,
    is_descending_alternating,
    max_movable_cards,
)
from freecell.core.card import SUIT_TO_INDEX
from freecell.solvers.BFS import BFSSolver

UnpackedMove = tuple[str, int, str, int, int]
T = TypeVar("T")


def _game_state_canonical_key(state: GameState) -> tuple[tuple[int, ...], tuple[int, ...], tuple[tuple[int, ...], ...]]:
    foundations = state.foundations
    freecells = tuple(sorted(63 if card is None else card_to_code(card) for card in state.freecells))
    cascades = tuple(
        sorted(tuple(card_to_code(card) for card in cascade) for cascade in state.cascades)
    )
    return foundations, freecells, cascades


def _iter_legal_moves_unpacked(state: GameState):
    # Keep the same ordering as BaseSolver to keep probes comparable.

    # cascade -> foundation
    for source_index, cascade in enumerate(state.cascades):
        if not cascade:
            continue
        top = cascade[-1]
        suit_index = SUIT_TO_INDEX[top.suit]
        if can_move_to_foundation(top, state.foundations[suit_index]):
            yield ("cascade", source_index, "foundation", 0, 1)

    # freecell -> foundation
    for source_index, card in enumerate(state.freecells):
        if card is None:
            continue
        suit_index = SUIT_TO_INDEX[card.suit]
        if can_move_to_foundation(card, state.foundations[suit_index]):
            yield ("freecell", source_index, "foundation", 0, 1)

    # freecell -> cascade
    for source_index, card in enumerate(state.freecells):
        if card is None:
            continue
        for destination_index in range(len(state.cascades)):
            destination = state.cascades[destination_index]
            destination_top = destination[-1] if destination else None
            if can_stack_on_cascade(card, destination_top):
                yield ("freecell", source_index, "cascade", destination_index, 1)

    # cascade -> cascade (with sequence moves)
    empty_cascades_total = sum(1 for cascade in state.cascades if not cascade)
    empty_freecells_total = sum(1 for card in state.freecells if card is None)

    for source_index, source in enumerate(state.cascades):
        source_len = len(source)
        if source_len == 0:
            continue

        for destination_index, destination in enumerate(state.cascades):
            if source_index == destination_index:
                continue

            destination_len = len(destination)
            destination_is_empty = destination_len == 0
            destination_top = destination[-1] if destination else None
            auxiliary_empty_cascades = empty_cascades_total - (1 if destination_is_empty else 0)
            max_count = min(
                source_len,
                max_movable_cards(empty_freecells_total, auxiliary_empty_cascades),
            )

            for count in range(1, max_count + 1):
                moving_stack = source[-count:]
                if not is_descending_alternating(moving_stack):
                    continue
                if can_stack_on_cascade(moving_stack[0], destination_top):
                    yield ("cascade", source_index, "cascade", destination_index, count)

    # cascade -> freecell (send to the first empty slot only)
    empty_slots = [index for index, card in enumerate(state.freecells) if card is None]
    if empty_slots:
        first_empty = empty_slots[0]
        for source_index, cascade in enumerate(state.cascades):
            if cascade:
                yield ("cascade", source_index, "freecell", first_empty, 1)


def _replace_tuple_item(items: tuple[T, ...], index: int, value: T) -> tuple[T, ...]:
    mutable = list(items)
    mutable[index] = value
    return tuple(mutable)


def _increment_foundation(
    foundations: tuple[int, int, int, int],
    suit_index: int,
) -> tuple[int, int, int, int]:
    values = list(foundations)
    values[suit_index] += 1
    return (values[0], values[1], values[2], values[3])


def _apply_move_unpacked(state: GameState, move: UnpackedMove) -> GameState:
    source, source_index, destination, destination_index, count = move

    cascades = state.cascades
    freecells = state.freecells
    foundations = state.foundations

    if source == "cascade" and destination == "freecell":
        source_cascade = cascades[source_index]
        moving = source_cascade[-1]
        new_source = source_cascade[:-1]
        new_cascades = _replace_tuple_item(cascades, source_index, new_source)
        new_freecells = _replace_tuple_item(freecells, destination_index, moving)
        return GameState(cascades=new_cascades, freecells=new_freecells, foundations=foundations)

    if source == "freecell" and destination == "cascade":
        moving = freecells[source_index]
        if moving is None:
            raise ValueError("Illegal move: freecell source is empty")
        destination_cascade = cascades[destination_index]
        new_destination = destination_cascade + (moving,)
        new_cascades = _replace_tuple_item(cascades, destination_index, new_destination)
        new_freecells = _replace_tuple_item(freecells, source_index, None)
        return GameState(cascades=new_cascades, freecells=new_freecells, foundations=foundations)

    if source == "cascade" and destination == "foundation":
        source_cascade = cascades[source_index]
        moving = source_cascade[-1]
        suit_index = SUIT_TO_INDEX[moving.suit]
        new_source = source_cascade[:-1]
        new_cascades = _replace_tuple_item(cascades, source_index, new_source)
        new_foundations = _increment_foundation(foundations, suit_index)
        return GameState(cascades=new_cascades, freecells=freecells, foundations=new_foundations)

    if source == "freecell" and destination == "foundation":
        moving = freecells[source_index]
        if moving is None:
            raise ValueError("Illegal move: freecell source is empty")
        suit_index = SUIT_TO_INDEX[moving.suit]
        new_freecells = _replace_tuple_item(freecells, source_index, None)
        new_foundations = _increment_foundation(foundations, suit_index)
        return GameState(cascades=cascades, freecells=new_freecells, foundations=new_foundations)

    if source == "cascade" and destination == "cascade":
        source_cascade = cascades[source_index]
        destination_cascade = cascades[destination_index]
        moving_stack: tuple[Card, ...] = source_cascade[-count:]
        new_source = source_cascade[:-count]
        new_destination = destination_cascade + moving_stack
        new_cascades = list(cascades)
        new_cascades[source_index] = new_source
        new_cascades[destination_index] = new_destination
        return GameState(cascades=tuple(new_cascades), freecells=freecells, foundations=foundations)

    raise ValueError(f"Unsupported move type: {move}")


def run_probe_packed(
    seed: int,
    target_expansions: int,
    *,
    trace_memory: bool = False,
) -> tuple[int, int, float, int]:
    initial = GameState.initial(seed=seed).to_packed()
    solver = BFSSolver()

    queue: deque[PackedState] = deque([initial])
    seen: set[Hashable] = {initial.canonical_key()}
    expanded = 0

    if trace_memory:
        tracemalloc.start()
    started = perf_counter()
    while queue and expanded < target_expansions:
        state = queue.popleft()
        expanded += 1

        for move in solver.iter_legal_moves(state):
            next_state = state.apply_raw_move(move, validate=False)
            next_key = next_state.canonical_key()
            if next_key in seen:
                continue
            seen.add(next_key)
            queue.append(next_state)

    elapsed = perf_counter() - started
    peak_memory = 0
    if trace_memory:
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return expanded, len(seen), elapsed, peak_memory


def run_probe_unpacked(
    seed: int,
    target_expansions: int,
    *,
    trace_memory: bool = False,
) -> tuple[int, int, float, int]:
    initial = GameState.initial(seed=seed)

    queue: deque[GameState] = deque([initial])
    seen: set[Hashable] = {_game_state_canonical_key(initial)}
    expanded = 0

    if trace_memory:
        tracemalloc.start()
    started = perf_counter()
    while queue and expanded < target_expansions:
        state = queue.popleft()
        expanded += 1

        for move in _iter_legal_moves_unpacked(state):
            next_state = _apply_move_unpacked(state, move)
            next_key = _game_state_canonical_key(next_state)
            if next_key in seen:
                continue
            seen.add(next_key)
            queue.append(next_state)

    elapsed = perf_counter() - started
    peak_memory = 0
    if trace_memory:
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return expanded, len(seen), elapsed, peak_memory


def benchmark(seed: int = 1, target_expansions: int = 1500, trials: int = 5) -> None:
    packed_times: list[float] = []
    unpacked_times: list[float] = []
    packed_peak_memories: list[int] = []
    unpacked_peak_memories: list[int] = []

    run_probe_packed(seed=seed, target_expansions=300)
    run_probe_unpacked(seed=seed, target_expansions=300)

    for _ in range(trials):
        packed_expanded, packed_unique, packed_elapsed, _ = run_probe_packed(
            seed=seed,
            target_expansions=target_expansions,
        )
        unpacked_expanded, unpacked_unique, unpacked_elapsed, _ = run_probe_unpacked(
            seed=seed,
            target_expansions=target_expansions,
        )

        packed_times.append(packed_elapsed)
        unpacked_times.append(unpacked_elapsed)

    # Sample peak memory in dedicated runs, because tracemalloc significantly
    # slows execution and would skew speed comparisons.
    memory_trials = max(2, min(trials, 3))
    for _ in range(memory_trials):
        _, _, _, packed_peak_memory = run_probe_packed(
            seed=seed,
            target_expansions=target_expansions,
            trace_memory=True,
        )
        _, _, _, unpacked_peak_memory = run_probe_unpacked(
            seed=seed,
            target_expansions=target_expansions,
            trace_memory=True,
        )
        packed_peak_memories.append(packed_peak_memory)
        unpacked_peak_memories.append(unpacked_peak_memory)

    packed_mean = mean(packed_times)
    unpacked_mean = mean(unpacked_times)

    packed_rate = packed_expanded / packed_mean if packed_mean > 0 else 0.0
    unpacked_rate = unpacked_expanded / unpacked_mean if unpacked_mean > 0 else 0.0
    speedup = packed_rate / unpacked_rate if unpacked_rate > 0 else 0.0
    packed_peak_mean_mb = mean(packed_peak_memories) / (1024 * 1024)
    unpacked_peak_mean_mb = mean(unpacked_peak_memories) / (1024 * 1024)
    packed_bytes_per_unique = (mean(packed_peak_memories) / packed_unique) if packed_unique > 0 else 0.0
    unpacked_bytes_per_unique = (mean(unpacked_peak_memories) / unpacked_unique) if unpacked_unique > 0 else 0.0
    memory_ratio = (unpacked_peak_mean_mb / packed_peak_mean_mb) if packed_peak_mean_mb > 0 else 0.0

    print("=== BFS Expansion Speed (Canonical Mode) ===")
    print("packed_dedup=canonical_key() unpacked_dedup=canonical_tuple_key")
    print(f"seed={seed} target_expansions={target_expansions} trials={trials}")
    print(f"packed_unique_last_trial={packed_unique}")
    print(f"unpacked_unique_last_trial={unpacked_unique}")
    print(f"packed_mean={packed_mean:.6f}s packed_rate={packed_rate:.2f} nodes/s")
    print(f"unpacked_mean={unpacked_mean:.6f}s unpacked_rate={unpacked_rate:.2f} nodes/s")
    print(f"packed_over_unpacked_speed={speedup:.3f}x")
    print("=== BFS Peak Memory (tracemalloc) ===")
    print(f"memory_trials={memory_trials}")
    print(f"packed_peak_mean={packed_peak_mean_mb:.3f} MB")
    print(f"unpacked_peak_mean={unpacked_peak_mean_mb:.3f} MB")
    print(f"unpacked_over_packed_memory={memory_ratio:.3f}x")
    print(f"packed_bytes_per_unique_state={packed_bytes_per_unique:.1f}")
    print(f"unpacked_bytes_per_unique_state={unpacked_bytes_per_unique:.1f}")


def main() -> None:
    seed = 1
    target_expansions = 1500
    trials = 5
    benchmark(seed=seed, target_expansions=target_expansions, trials=trials)


if __name__ == "__main__":
    main()
