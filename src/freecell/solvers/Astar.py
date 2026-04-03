from freecell.core.card import SUIT_TO_INDEX, SUITS

from .BestFS import BestFSSolver
from ..core.move_engine import CASCADE, FREECELL, FOUNDATION
from .base import RawMove
from ..core import PackedState
from ..core.rules import is_descending_alternating_codes
from collections.abc import Callable, Sequence

HeuristicFn = Callable[[PackedState], float]
HeuristicSpec = tuple[HeuristicFn, float]
StepCostFn = Callable[[RawMove, PackedState], int]


class AstarSolver(BestFSSolver):
    def __init__(
        self,
        heuristics: Sequence[HeuristicSpec] | None = None,
        *,
        step_cost_fn: StepCostFn | None = None,
        max_expansions: int | None = None,
        heuristic_weight: float = 1.0,
    ):
        super().__init__(max_expansions=max_expansions)
        self.heuristic_weight = heuristic_weight

        default_heuristics: tuple[HeuristicSpec, ...] = (
            (self.h_cards_remaining, 1.5),
            (self.h_occupied_freecells, 1.5),
            (self.h_disorder, 1.5),
           
        )
        specs = tuple(heuristics) if heuristics is not None else default_heuristics
        if not specs:
            raise ValueError("heuristics must contain at least one (callable, weight) pair")

        normalized: list[HeuristicSpec] = []
        for heuristic_fn, weight in specs:
            if not callable(heuristic_fn):
                raise TypeError("heuristic must be callable")
            normalized.append((heuristic_fn, float(weight)))

        self._heuristics = tuple(normalized)
        self._step_cost_fn = step_cost_fn or self._default_step_cost

    def evaluate(
        self, 
        parent_g: int, 
        move: RawMove | None,
        state: PackedState,
    ) -> tuple[float, int]:
        """
        Calculates f(n) = g(n) + W * h(n).
        g: number of moves taken from start.
        W: heuristic weight.
        h: estimated moves to goal.
        """
        step_cost = 0 if move is None else self._step_cost_fn(move, state)
        if step_cost < 0:
            raise ValueError("step_cost_fn must return a non-negative integer")

        new_g = parent_g + step_cost
        h = self._combined_heuristic(state)
        return (new_g + self.heuristic_weight * h, step_cost)

    @staticmethod
    def _default_step_cost(move: RawMove, state: PackedState) -> int:
        # Keep default move-cost preference consistent with previous behavior.
        weight = 1
        if move:
            # Move format: (src, src_idx, dst, dst_idx, count)
            src, src_idx, dst, dst_idx, count = move
            if dst == FOUNDATION:
                weight = 1 # Encouraged
            elif dst == FREECELL:
                weight = 4 # Discouraged (resource consumption)
            elif dst == CASCADE:
                # Check if column is empty
                if state.cascade_length(dst_idx) == count:
                    if count == 1:
                        weight = 4 # Waste an empty column just to move one card
                    else:
                        weight = 1 # Moving multiple cards to an empty column is fine
                else:
                    weight = 2 # Moving multiple cards to a non-empty column is fine
            
            # Move multiple cards to structure the cascade is good
            if src == CASCADE and dst == CASCADE and count > 1:
                weight = max(1, weight - 1)
        return weight

    def _combined_heuristic(self, state: PackedState) -> float:
        # sum_spec_weights = sum(weight for _, weight in self._heuristics)
        return sum(weight * heuristic_fn(state) for heuristic_fn, weight in self._heuristics) #/ sum_spec_weights

    @staticmethod
    def h_cards_remaining(state: PackedState) -> float:
        return float(state.cards_remaining())

    @staticmethod
    def h_occupied_freecells(state: PackedState) -> float:
        empty_freecells = state.freecell_count_empty()
        return float(state.freecell_slot_count - empty_freecells)
    
    def h_empty_columns(self, state: PackedState) -> float:
        return float(state.cascade_count_empty())
    
    def h_disorder(self, state: PackedState) -> float:
        return float(self._calculate_disorder(state))

    def h_suit_blocking(self, state: PackedState) -> float:
        from ..core.card import SUITS, SUIT_TO_INDEX, Card, card_to_code, code_to_card
        
        # Get the foundation targets (next card needed for each suit)
        targets_set = set()
        for suit in SUITS:
            suit_idx = SUIT_TO_INDEX[suit]
            current_rank = state.foundation_rank(suit_idx)
            if current_rank < 13:
                next_rank = current_rank + 1
                target_card = Card(next_rank, suit)
                targets_set.add(card_to_code(target_card))
        
        extra_moves = 0
        for c_idx in range(state.cascade_count):
            length = state.cascade_length(c_idx)
            for pos in range(length):
                card_code = state.cascade_card_code(c_idx, pos)
                
                if card_code in targets_set:
                    if pos == length - 1:
                        break # Target is already exposed
                    
                    # Get the codes of all cards sitting ON TOP of the target
                    blocker_codes = [state.cascade_card_code(c_idx, i) 
                                    for i in range(pos + 1, length)]
                    
                    num_blocks = 1
                    for i in range(len(blocker_codes) - 1):
                        # If the next card doesn't follow the rule, it starts a NEW block
                        if not is_descending_alternating_codes(blocker_codes[i:i+2]):
                            num_blocks += 1
                    
                    extra_moves += num_blocks
                    break 
        
        return float(extra_moves)

    def h_next_to_foundation(self, state: PackedState) -> float:
        from ..core.card import SUITS, SUIT_TO_INDEX, Card, card_to_code

        # Next needed cards for each suit
        targets = set()
        for suit in SUITS:
            suit_idx = SUIT_TO_INDEX[suit]
            current_rank = state.foundation_rank(suit_idx)
            if current_rank < 13:
                next_rank = current_rank + 1
                targets.add(card_to_code(Card(next_rank, suit)))

        # Check if any target is already movable to foundation from cascade tops or freecell
        for c_idx in range(state.cascade_count):
            length = state.cascade_length(c_idx)
            if length > 0 and state.cascade_card_code(c_idx, length - 1) in targets:
                return -100.0

        for fc_idx in range(state.freecell_slot_count):
            fc_code = state.freecell(fc_idx)
            if fc_code != 63 and fc_code in targets:
                return -100.0

        return 0.0

    def _calculate_disorder(self, state: PackedState) -> int:
        total_disorder = 0
        for c_idx in range(state.cascade_count):
            length = state.cascade_length(c_idx)
            if length <= 1:
                continue
                
            # Get all card codes in this cascade at once
            # This is much faster than calling a method for every single card
            cards = state.cascade_tail_codes(c_idx, length)
            
            for i in range(length - 1):
                # Check the pair: cards[i] and cards[i+1]
                # We pass a slice of 2 cards to your existing rule checker
                if not is_descending_alternating_codes(cards[i : i+2]):
                    # If they don't match, everything below index 'i' is disordered
                    total_disorder += (length - i - 1)
                    break                 
        return total_disorder