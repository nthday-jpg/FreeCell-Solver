import pygame
from freecell.GUI.scenes.base_scene import BaseScene
from freecell.GUI.core.constants import TEXT_COLOR
from freecell.GUI.ui.components import draw_buttons, draw_slider
from freecell.GUI.core.settings import save_settings

class SettingsScene(BaseScene):
    def __init__(self, screen, assets, audio, settings, change_scene):
        super().__init__(screen, assets, audio, settings, change_scene)

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        button = self._settings_buttons(events)
        if button == "Toggle Music Mute":
            self.settings.music_muted = not self.settings.music_muted
        elif button == "Toggle SFX Mute":
            self.settings.sfx_muted = not self.settings.sfx_muted
        elif button == "Back":
            save_settings(self.settings)
            self.audio.apply_settings()
            self.change_scene("menu")

    def _settings_buttons(self, events: list[pygame.event.Event]) -> str | None:
        center_x = self.screen.get_rect().centerx
        start_y = 460
        gap = 18
        defs = [
            ("Toggle Music Mute", pygame.Rect(center_x - 130, start_y, 260, 44)),
            ("Toggle SFX Mute", pygame.Rect(center_x - 130, start_y + 44 + gap, 260, 44)),
            ("Back", pygame.Rect(center_x - 130, start_y + 2 * (44 + gap) + 8, 260, 50)),
        ]
        return draw_buttons(self.screen, self.assets.body_font, defs, events)

    def render(self) -> None:
        self.screen.fill((22, 56, 80))
        center_x = self.screen.get_rect().centerx

        title = self.assets.title_font.render("Settings", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(center_x, 120)))

        self.settings.music_volume = draw_slider(self.screen, self.assets.body_font, "Music Volume", self.settings.music_volume, 0, 100, 220)
        self.settings.sfx_volume = draw_slider(self.screen, self.assets.body_font, "SFX Volume", self.settings.sfx_volume, 0, 100, 280)

        self.audio.apply_settings()

        hint = self.assets.small_font.render(
            "Solver is chosen in-game (Solver button). Volume range: 0-100. Save when leaving.",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(hint, hint.get_rect(center=(center_x, 400)))

        info = self.assets.small_font.render("Save is automatic when leaving this screen.", True, TEXT_COLOR)
        self.screen.blit(info, info.get_rect(center=(center_x, 680)))
        ext = self.assets.small_font.render(
            "External audio folder: set `external_audio_dir` in .freecell_gui_settings.json or FREECELL_AUDIO_DIR.",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(ext, ext.get_rect(center=(center_x, 705)))

        self._settings_buttons([])
