# GUI - Game Core Integration

This guide explains how to use the FreeCell game core (`src/freecell/core/`) from a GUI application.

## Quick Start

```python
from src.freecell.core.state import GameState, Move

# 1. Create a new game
game = GameState.initial(seed=1)  # Deal #1

# 2. Get initial board state
print(f"Cascades: {game.cascades}")
print(f"Freecells: {game.freecells}")
print(f"Foundations: {game.foundations}")

# 3. Apply a move
move = Move(
    source="cascade",
    source_index=0,
    destination="freecell",
    destination_index=0,
    count=1
)
game = game.apply_move(move)

# 4. Check if won
if game.is_victory:
    print("You won!")
```

## Core Concepts

### GameState

**GameState** is the main representation for GUI development:
- `cascades: tuple[tuple[Card, ...], ...]` - 8 columns of cards
- `freecells: tuple[Card | None, ...]` - 4 slots (None if empty)
- `foundations: tuple[int, int, int, int]` - Current rank in each suit (0-13)
- Immutable and hashable (frozen dataclass)
- All you need for display and user interaction

### Card Representation

```python
from src.freecell.core.card import Card

card = Card(rank=13, suit="H")  # King of Hearts
print(card.short_name)  # "KH"
print(card.color)       # "red"

# Parse from string
card = Card.from_short_name("KH")
```

Valid ranks: 1-13 (Ace through King)
Valid suits: "C", "D", "H", "S" (Clubs, Diamonds, Hearts, Spades)

## Managing Game State

### Creating Games

```python
# New game from deal number (Microsoft deals)
game = GameState.initial(seed=1)        # Deal #1
game = GameState.initial(seed=123456)   # Deal #123,456

# Empty game (for testing)
game = GameState(
    cascades=((), () , (), (), (), (), (), ()),
    freecells=(None, None, None, None),
    foundations=(0, 0, 0, 0)
)
```

### Getting Board Information

```python
# Card access
top_card = game.cascade_top(0)  # Top card of cascade 0, or None if empty

freecell_card = game.freecells[0]  # None if empty

# Counts
cards_in_foundation = game.cards_in_foundation  # 0-52
cards_remaining = game.cards_remaining         # 52 - in_foundation

# Progress
progress = game.progress_ratio   # 0.0 to 1.0

# Foundation state
ranks = game.foundation_summary()  # {"C": 5, "D": 3, "H": 0, "S": 0}
clubs_rank = game.foundation_rank("C")
```

## Working with Moves

### Move Structure

```python
from src.freecell.core.state import Move

move = Move(
    source="cascade",           # "cascade", "freecell", or "foundation"
    source_index=0,             # Index 0-7 (cascade), 0-3 (freecell), 0 (foundation)
    destination="freecell",     # "cascade", "freecell", or "foundation"
    destination_index=0,        # Target index
    count=1                      # Number of cards (usually 1, cascade-to-cascade can be >1)
)
```

### Applying Moves

```python
# Apply a single move
try:
    new_game = game.apply_move(move)
except ValueError as e:
    print(f"Illegal move: {e}")

# Note: GameState is immutable (frozen dataclass)
# apply_move() returns a new GameState instance
```

### Move Validation

The core automatically validates moves. Common errors:

```python
# Empty source
Move(source="cascade", source_index=0, ...)  # Error if cascade is empty

# Occupied target
Move(source="cascade", destination="freecell", destination_index=0, ...)
# Error if freecell 0 already has a card

# Invalid stacking
Move(source="cascade", destination="cascade", ...)
# Error if the moving card(s) violate stacking rules
# Rules: Descending rank, alternating color

# Insufficient moves allowed
Move(source="cascade", destination="cascade", count=5, ...)
# Error if not enough free spaces to move that many cards
```

## Common GUI Patterns

### Display the Board

```python
def display_board(game: GameState):
    print("\n=== FreeCell Board ===\n")
    
    # Cascades (8 columns)
    print("Cascades:")
    for i, cascade in enumerate(game.cascades):
        cards_str = " ".join(c.short_name for c in cascade) if cascade else "[empty]"
        print(f"  {i}: {cards_str}")
    
    # Freecells (4 slots)
    print("\nFreecells:")
    freecells_str = " | ".join(
        c.short_name if c else "[empty]"
        for c in game.freecells
    )
    print(f"  {freecells_str}")
    
    # Foundations (4 piles)
    print("\nFoundations:")
    suits = ["C", "D", "H", "S"]
    for suit, rank in zip(suits, game.foundations):
        print(f"  {suit}: {rank}")
    
    print(f"\nProgress: {game.progress_ratio:.1%}")
```

### Undo History

```python
from collections import deque

class GameHistory:
    def __init__(self, initial_game: GameState):
        self.history: deque[GameState] = deque([initial_game])
        self.current_index = 0
    
    def apply_move(self, move: Move) -> bool:
        try:
            current = self.history[self.current_index]
            new_game = current.apply_move(move)
            
            # Remove any redo history
            while len(self.history) > self.current_index + 1:
                self.history.pop()
            
            self.history.append(new_game)
            self.current_index += 1
            return True
        except ValueError:
            return False
    
    def undo(self) -> bool:
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False
    
    def redo(self) -> bool:
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return True
        return False
    
    @property
    def current_game(self) -> GameState:
        return self.history[self.current_index]
    
    @property
    def move_count(self) -> int:
        return self.current_index
```

### Move Suggestions

```python
def get_all_legal_moves_naive(game: GameState) -> list[Move]:
    """Simple way to get legal moves (for UI hints)."""
    # Try each possible move and catch errors
    moves = []
    
    # Cascade to Freecell
    for i in range(8):
        if game.cascades[i]:
            for j in range(4):
                if game.freecells[j] is None:
                    move = Move(source="cascade", source_index=i, 
                               destination="freecell", destination_index=j)
                    try:
                        game.apply_move(move)
                        moves.append(move)
                    except ValueError:
                        pass
    
    # Cascade to Foundation
    for i in range(8):
        if game.cascades[i]:
            move = Move(source="cascade", source_index=i,
                       destination="foundation", destination_index=0)
            try:
                game.apply_move(move)
                moves.append(move)
            except ValueError:
                pass
    
    # ... similar for other move types
    return moves
```

**Note:** For exhaustive move generation, use the solver framework (see [solvers/README.md](../solvers/README.md)).

### Auto-Play Foundation Moves

```python
def auto_play_to_foundation(game: GameState) -> GameState:
    """Repeatedly move cards to foundation when possible."""
    while True:
        moved = False
        
        # Check cascades
        for i, cascade in enumerate(game.cascades):
            if not cascade:
                continue
            card = cascade[-1]
            suit = card.suit
            current_rank = game.foundation_rank(suit)
            
            if card.rank == current_rank + 1:
                move = Move(
                    source="cascade",
                    source_index=i,
                    destination="foundation",
                    destination_index=0
                )
                try:
                    game = game.apply_move(move)
                    moved = True
                    break
                except ValueError:
                    pass
        
        # Check freecells
        if not moved:
            for i, card in enumerate(game.freecells):
                if card is None:
                    continue
                suit = card.suit
                current_rank = game.foundation_rank(suit)
                
                if card.rank == current_rank + 1:
                    move = Move(
                        source="freecell",
                        source_index=i,
                        destination="foundation",
                        destination_index=0
                    )
                    try:
                        game = game.apply_move(move)
                        moved = True
                        break
                    except ValueError:
                        pass
        
        if not moved:
            break
    
    return game
```

## Performance Considerations

### Caching

```python
import functools
from src.freecell.core.state import GameState, Move

# GameState is immutable and hashable (frozen dataclass)
# Safe to use as dict keys or cache decorator argument
@functools.cache
def get_board_display(game: GameState) -> str:
    # Expensive display rendering
    return render_board(game)
```

### Immutability

Always remember `GameState` is immutable:

```python
game = GameState.initial(seed=1)
move = Move(source="cascade", source_index=0, destination="freecell", destination_index=0)

new_game = game.apply_move(move)  # Returns NEW GameState
# game is still unchanged
```

## Error Handling

```python
from src.freecell.core.state import Move, GameState

def safe_move(game: GameState, move: Move) -> tuple[bool, GameState, str]:
    """Apply move with error handling."""
    try:
        new_game = game.apply_move(move)
        return True, new_game, ""
    except ValueError as e:
        return False, game, str(e)

# Usage
success, new_game, error_msg = safe_move(game, move)
if success:
    game = new_game
else:
    print(f"Move failed: {error_msg}")
```

## Integration Example

```python
class FreeCell:
    def __init__(self, deal: int):
        self.game = GameState.initial(seed=deal)
        self.history = GameHistory(self.game)
    
    def make_move(self, move: Move) -> bool:
        success = self.history.apply_move(move)
        if success:
            current = self.history.current_game
            # Auto-play foundation
            current = auto_play_to_foundation(current)
            self.history.history[self.history.current_index] = current
        return success
    
    def get_state(self) -> GameState:
        return self.history.current_game
    
    def is_won(self) -> bool:
        return self.get_state().is_victory
    
    def get_moves(self) -> int:
        return self.history.move_count
    
    def undo(self) -> bool:
        return self.history.undo()

# Usage
fc = FreeCell(deal=1)
while not fc.is_won():
    display_board(fc.get_state())
    move = get_user_move()
    if fc.make_move(move):
        print("Move accepted")
    else:
        print("Illegal move")
```

---

For questions about game rules, see [core/rules.py](../core/rules.py). For card details, see [core/card.py](../core/card.py).