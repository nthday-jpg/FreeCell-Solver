import pygame
from typing import Callable
from freecell.GUI.managers.assets import AssetManager
from freecell.GUI.managers.audio import AudioManager
from freecell.GUI.core.settings import GuiSettings

class BaseScene:
    def __init__(self, screen: pygame.Surface, assets: AssetManager, audio: AudioManager, settings: GuiSettings, change_scene: Callable[..., None]) -> None:
        self.screen = screen
        self.assets = assets
        self.audio = audio
        self.settings = settings
        self.change_scene = change_scene

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass

    def render(self) -> None:
        pass
