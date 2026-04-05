from pathlib import Path
import os
import pygame
from freecell.GUI.core.settings import GuiSettings

class AudioManager:
    def __init__(self, settings: GuiSettings) -> None:
        self.settings = settings
        self.assets_dir = Path(__file__).resolve().parent.parent / "assets"
        self._audio_root: Path | None = None
        self.music_tracks: dict[str, Path] = {}
        self.sfx_tracks: dict[str, Path] = {}
        self.sfx_cache: dict[str, pygame.mixer.Sound] = {}
        self.current_music = ""
        self.enabled = False
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False

        self.apply_settings()

    def _resolve_audio_root(self) -> Path:
        candidate = self.settings.external_audio_dir.strip()
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists() and path.is_dir():
                return path

        env_path = os.environ.get("FREECELL_AUDIO_DIR", "").strip()
        if env_path:
            path = Path(env_path).expanduser()
            if path.exists() and path.is_dir():
                return path

        return self.assets_dir

    def _build_track_maps(self, root: Path) -> None:
        # Support both layouts:
        # - root/menu_music.ogg (older layout)
        # - root/music/menu_music.ogg (your current layout)
        music_dir = root / "music"
        if music_dir.exists() and music_dir.is_dir():
            music_root = music_dir
        else:
            music_root = root

        self.music_tracks = {
            "menu": music_root / "menu_music.ogg",
            "game": music_root / "game_music.ogg",
            "win": music_root / "win_music.ogg",
        }
        self.sfx_tracks = {
            "move_ok": root / "move_ok.wav",
            "move_fail": root / "move_fail.wav",
        }

    def apply_settings(self) -> None:
        if not self.enabled:
            return

        root = self._resolve_audio_root()
        if self._audio_root != root:
            self._audio_root = root
            self._build_track_maps(root)
            self.sfx_cache.clear()
            self.current_music = ""

        music_ratio = max(0.0, min(100.0, float(self.settings.music_volume))) / 100.0
        volume = 0.0 if self.settings.music_muted else music_ratio
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
        sfx_ratio = max(0.0, min(100.0, float(self.settings.sfx_volume))) / 100.0
        sound.set_volume(sfx_ratio)
        sound.play()
