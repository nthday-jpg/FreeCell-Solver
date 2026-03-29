from dataclasses import dataclass
from typing import Literal

PileType = Literal["cascade", "freecell", "foundation"]


@dataclass(frozen=True, slots=True)
class Move:
	source: PileType
	source_index: int
	destination: PileType
	destination_index: int
	count: int = 1


# Move representation: (source_type, source_index, destination_type, destination_index, count)
# source_type/destination_type: CASCADE (0), FREECELL (1), or FOUNDATION (2)
RawMove = tuple[int, int, int, int, int]
