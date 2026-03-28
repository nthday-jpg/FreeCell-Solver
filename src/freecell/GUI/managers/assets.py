from pathlib import Path
import pygame
from freecell.core.card import SUITS, RANK_TO_NAME

class AssetManager:
    def __init__(self) -> None:
        self.title_font = pygame.font.SysFont("cambria", 46, bold=True)
        self.body_font = pygame.font.SysFont("consolas", 22)
        self.small_font = pygame.font.SysFont("consolas", 18)

        self.card_images: dict[str, pygame.Surface] = {}
        self._load_cards()

    def _load_cards(self) -> None:
        assets_dir = Path(__file__).resolve().parent.parent / "assets" / "cards"

        suit_folder_map = {"C": "Clubs", "D": "Diamonds", "H": "Hearts", "S": "Spades"}
        rank_file_map = {
            1: "ace", 2: "2", 3: "3", 4: "4", 5: "5", 
            6: "6", 7: "7", 8: "8", 9: "9", 10: "10", 
            11: "jack", 12: "queen", 13: "king"
        }
        
        for suit in SUITS:
            for rank in range(1, 14):
                card_name = f"{RANK_TO_NAME[rank]}{suit}"
                folder_name = suit_folder_map[suit]
                file_name = rank_file_map[rank]
                img_path = assets_dir / folder_name / f"{file_name}.png"
                
                try:
                    image = pygame.image.load(str(img_path)).convert_alpha()
                    self.card_images[card_name] = pygame.transform.smoothscale(image, (100, 140))
                except FileNotFoundError:
                    pass
