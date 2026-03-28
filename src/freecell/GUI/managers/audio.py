from pathlib import Path
import pygame
from freecell.GUI.core.settings import GuiSettings

class AudioManager:
    def __init__(self, settings: GuiSettings) -> None:
        self.settings = settings
        self.assets_dir = Path(__file__).resolve().parent.parent / "assets"
        self.music_tracks = {
            "menu": self.assets_dir / "menu_music.ogg",
            "game": self.assets_dir / "game_music.ogg",
            "win": self.assets_dir / "win_music.ogg",
        }
        self.sfx_tracks = {
            "move_ok": self.assets_dir / "move_ok.wav",
            "move_fail": self.assets_dir / "move_fail.wav",
        }
        self.sfx_cache: dict[str, pygame.mixer.Sound] = {}
        self.current_music = ""
        self.enabled = False
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False

        self.apply_settings()

    def apply_settings(self) -> None:
        if not self.enabled:
            return
        volume = 0.0 if self.settings.music_muted else max(0.0, min(1.0, self.settings.music_volume))
        pygame.mixer.music.set_volume(volume)

    def play_music(self, key: str) -> None:
        if not self.enabled or self.current_music == key:
            return
        track = self.music_tracks.get(key)
        if track is None or not track.exists() or self.settings.music_muted:
            return
        try:
            pygame.mixer.music.load(str(track))
            pygame.mixer.music.play(-1)
            self.current_music = key
        except pygame.error:
            self.current_music = ""

    def play_sfx(self, key: str) -> None:
        if not self.enabled or self.settings.sfx_muted:
            return
        track = self.sfx_tracks.get(key)
        if track is None or not track.exists():
            return
        sound = self.sfx_cache.get(key)
        if sound is None:
            try:
                sound = pygame.mixer.Sound(str(track))
            except pygame.error:
                return
            self.sfx_cache[key] = sound
        sound.set_volume(max(0.0, min(1.0, self.settings.sfx_volume)))
        sound.play()
