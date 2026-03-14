from dataclasses import dataclass

SUITS: tuple[str, ...] = ("C", "D", "H", "S")
SUIT_TO_INDEX: dict[str, int] = {suit: idx for idx, suit in enumerate(SUITS)}

RANK_TO_NAME: dict[int, str] = {
	1: "A",
	2: "2",
	3: "3",
	4: "4",
	5: "5",
	6: "6",
	7: "7",
	8: "8",
	9: "9",
	10: "10",
	11: "J",
	12: "Q",
	13: "K",
}
NAME_TO_RANK: dict[str, int] = {name: rank for rank, name in RANK_TO_NAME.items()}


@dataclass(frozen=True, slots=True)
class Card:
	rank: int
	suit: str

	def __post_init__(self) -> None:
		if self.rank not in RANK_TO_NAME:
			raise ValueError(f"Invalid card rank: {self.rank}")
		if self.suit not in SUITS:
			raise ValueError(f"Invalid card suit: {self.suit}")

	@property
	def color(self) -> str:
		return "red" if self.suit in ("D", "H") else "black"

	@property
	def short_name(self) -> str:
		return f"{RANK_TO_NAME[self.rank]}{self.suit}"

	@classmethod
	def from_short_name(cls, value: str) -> "Card":
		cleaned = value.strip().upper()
		if len(cleaned) < 2:
			raise ValueError(f"Invalid card shorthand: {value!r}")
		suit = cleaned[-1]
		rank_name = cleaned[:-1]
		if rank_name not in NAME_TO_RANK:
			raise ValueError(f"Invalid card rank in shorthand: {value!r}")
		return cls(rank=NAME_TO_RANK[rank_name], suit=suit)

	def __str__(self) -> str:
		return self.short_name


def standard_deck() -> tuple[Card, ...]:
	return tuple(Card(rank=rank, suit=suit) for suit in SUITS for rank in range(1, 14))
