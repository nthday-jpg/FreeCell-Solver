# Bit field configuration
CARD_BITS = 6
CARD_MASK = (1 << CARD_BITS) - 1
CASCADE_LEN_BITS = 4
FOUNDATION_BITS = 4
CARD_CODE_COUNT = 52
EMPTY_CARD_CODE = 63 # Represents an empty slot in freecells

# Game dimensions
CASCADE_COUNT = 8
FREECELL_COUNT = 4
FOUNDATION_COUNT = 4
MAX_FOUNDATION_RANK = 13

# Complete foundation mask (used for victory condition)
FOUNDATION_COMPLETE_MASK = sum(
    MAX_FOUNDATION_RANK << (i * FOUNDATION_BITS)
    for i in range(FOUNDATION_COUNT)
)

# Move type constants
CASCADE = 0
FREECELL = 1
FOUNDATION = 2

# Magic number for random deal
MS_RAND_MULTIPLIER = 214013
MS_RAND_INCREMENT = 2531011
MS_RAND_MASK = 0x7FFFFFFF

# Backward-compatible re-export; canonical definition lives in move_types.py.
from .move_types import RawMove