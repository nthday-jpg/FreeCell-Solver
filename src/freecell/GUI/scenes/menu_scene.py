import pygame
from freecell.GUI.scenes.base_scene import BaseScene
from freecell.GUI.core.constants import BG_COLOR, TEXT_COLOR
from freecell.GUI.ui.components import draw_buttons

class MenuScene(BaseScene):
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        button = self._menu_buttons(events)
        if button == "Play Manual":
            self.change_scene("game", "manual")
        elif button == "Play Using Solver":
            self.change_scene("game", "solver")
        elif button == "Settings":
            self.change_scene("settings")
        elif button == "Quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _menu_buttons(self, events: list[pygame.event.Event]) -> str | None:
        center_x = self.screen.get_rect().centerx
        button_width = 260
        button_height = 52
        
        def make_rect(y_pos: int) -> pygame.Rect:
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.centerx = center_x
            rect.y = y_pos
            return rect

        defs = [
            ("Play Manual", make_rect(260)),
            ("Play Using Solver", make_rect(328)),
            ("Settings", make_rect(396)),
            ("Quit", make_rect(464)),
        ]
        return draw_buttons(self.screen, self.assets.body_font, defs, events)

    def render(self) -> None:
        self.screen.fill(BG_COLOR)
        center_x = self.screen.get_rect().centerx
        title = self.assets.title_font.render("FreeCell", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(center_x, 140)))
        self._menu_buttons([])
