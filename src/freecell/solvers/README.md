# FreeCell Solvers

This directory contains solver implementations for the FreeCell card game. A solver is an algorithm that finds a sequence of valid moves to win a FreeCell game, starting from any initial game state.

## Overview

All solvers inherit from `BaseSolver` and implement the `solve()` method. The base class provides:
- Move generation (`iter_legal_moves()`)
- State transition logic (`transition()`)
- Goal checking (`is_goal()`)
- Performance tracking (timing, memory usage, node expansion count)

## How to Implement a Solver

### 1. Create a New Class

Extend `BaseSolver` from `base.py`:

```python
from .base import BaseSolver, SolveResult
from ..core import PackedState, Move

class MyCustomSolver(BaseSolver):
    def solve(self, initial_state: PackedState) -> SolveResult:
        """
        Find a sequence of moves to win the game.
        
        Args:
            initial_state: The starting game state (packed representation)
            
        Returns:
            SolveResult containing:
            - solved: bool (True if game was solved)
            - moves: tuple of Move objects (the solution path)
            - expanded_nodes: int (number of states explored)
        """
        # Your algorithm implementation here
        pass
```

### 2. Implement the `solve()` Method

Your solver must:

1. **Explore the game state space** using `iter_legal_moves(initial_state)` to generate legal moves
2. **Track visited states** to avoid cycles (use `state.key()` for hashing)
3. **Check for victory** using `is_goal(state)`
4. **Apply moves** using `transition(state, move, validate=False)`
5. **Build the solution** by reconstructing the move sequence from initial state to goal

### 3. Return a SolveResult

```python
moves: tuple[Move, ...] = ...  # Your computed sequence
return self.build_result(
    solved=True,  # or False if unsolvable
    moves=moves,
    expanded_nodes=len(visited_states),
)
```

## Key Types and Methods

### PackedState
The efficient game state representation:
- **`cascade_length(index)`** - Cards in cascade 0-7
- **`freecell(index)`** - Card code in freecell 0-3 (63 = empty)
- **`foundation_rank(suit_index)`** - Current rank in foundation 0-3
- **`cascade_top(index)`** - Top card code in cascade
- **`is_victory`** - Property: True if all cards in foundations
- **`key()`** - Returns hashable tuple for state deduplication

### Move Types
Moves are tuples: `(source_type, source_index, destination_type, destination_index, count)`

Types: `CASCADE (0)`, `FREECELL (1)`, `FOUNDATION (2)`

### BaseSolver Helper Methods
- **`iter_legal_moves(state)`** - Generator yielding all legal `RawMove`s from state
- **`transition(state, move, validate=False)`** - Returns new state after applying move
- **`is_goal(state)`** - Checks if state is victory condition

## Example: Breadth-First Search

See `BFS.py` for a complete example using BFS to find the shortest solution:

```python
from collections import deque

class BFS(BaseSolver):
    def solve(self, initial_state: PackedState) -> SolveResult:
        if self.is_goal(initial_state):
            return self.build_result(solved=True, moves=(), expanded_nodes=0)
        
        queue = deque([initial_state])
        visited = {initial_state.key()}
        parent = {initial_state.key(): None}
        
        expanded = 0
        while queue:
            current = queue.popleft()
            expanded += 1
            
            for move in self.iter_legal_moves(current):
                next_state = self.transition(current, move, validate=False)
                
                if self.is_goal(next_state):
                    # Reconstruct path
                    moves = self._reconstruct_path(parent, next_state)
                    return self.build_result(
                        solved=True, 
                        moves=moves, 
                        expanded_nodes=expanded
                    )
                
                key = next_state.key()
                if key not in visited:
                    visited.add(key)
                    parent[key] = (current, move)
                    queue.append(next_state)
        
        return self.build_result(solved=False, moves=(), expanded_nodes=expanded)
```

## Performance Tips

1. **Use `validate=False`** when applying moves in your search to skip redundant checks
2. **Deduplicate states** using `state.key()` to avoid revisiting
3. **Prioritize moves** - Best-first or heuristic-guided search often beats BFS
4. **Move ordering**: Foundation moves < Freecell moves < Cascade moves reduce branching
5. **Memory efficiency**: Consider iterative deepening if memory is limited

## Testing Your Solver

```python
from src.freecell.core.deal_generator import generate_deal
from src.freecell.core.state import GameState
from src.freecell.core.packed_state import PackedState

# Generate a test deal
deal_number = 1
deal = generate_deal(deal_number)
game_state = GameState.from_deal(deal)
packed_state = PackedState.from_game_state(game_state)

# Run your solver
solver = MyCustomSolver()
result = solver.timed_solve(packed_state)

print(result)  # Shows: solved status, move count, time, memory, nodes expanded
```

## Adding Your Solver to the Module

1. Create your solver file: `my_solver.py`
2. Update `__init__.py`:
```python
from .my_solver import MyCustomSolver

__all__ = ["BFS", "MyCustomSolver"]
```

---

Happy solving! 🎴
