from dataclasses import dataclass

from .constants import CARD_CODE_COUNT

SUITS: tuple[str, ...] = ("C", "D", "H", "S")
SUIT_TO_INDEX: dict[str, int] = {suit: idx for idx, suit in enumerate(SUITS)}
INDEX_TO_SUIT: tuple[str, ...] = SUITS

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


"""
	Card encoding, decoding:
		card_id = (rank - 1) * 4 + suit_index
		rank = floor (card_id/4) + 1
		suit_idx = card_id % 4
"""	
def card_to_code(card: Card) -> int:
	return ((card.rank - 1) << 2) | SUIT_TO_INDEX[card.suit]


_CODE_TO_CARD: tuple[Card, ...] = tuple(
	Card(rank=(code >> 2) + 1, suit=INDEX_TO_SUIT[code & 0b11]) for code in range(CARD_CODE_COUNT)
)

CARD_CODE_RANK: tuple[int, ...] = tuple((code >> 2) + 1 for code in range(CARD_CODE_COUNT))
CARD_CODE_SUIT_INDEX: tuple[int, ...] = tuple(code & 0b11 for code in range(CARD_CODE_COUNT))
CARD_CODE_IS_RED: tuple[bool, ...] = tuple((code & 0b11) in (1, 2) for code in range(CARD_CODE_COUNT))


def code_to_card(code: int) -> Card:
	if code < 0 or code >= CARD_CODE_COUNT:
		raise ValueError(f"Invalid packed card code: {code}")
	return _CODE_TO_CARD[code]


def card_code_rank(code: int) -> int:
	if code < 0 or code >= CARD_CODE_COUNT:
		raise ValueError(f"Invalid packed card code: {code}")
	return CARD_CODE_RANK[code]


def card_code_suit_index(code: int) -> int:
	if code < 0 or code >= CARD_CODE_COUNT:
		raise ValueError(f"Invalid packed card code: {code}")
	return CARD_CODE_SUIT_INDEX[code]


def card_code_is_red(code: int) -> bool:
	if code < 0 or code >= CARD_CODE_COUNT:
		raise ValueError(f"Invalid packed card code: {code}")
	return CARD_CODE_IS_RED[code]
