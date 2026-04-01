import pygame
from multiprocessing import freeze_support

from freecell.GUI.core.constants import WINDOW_SIZE, FPS
from freecell.GUI.core.settings import load_settings, save_settings
from freecell.GUI.managers.audio import AudioManager
from freecell.GUI.managers.assets import AssetManager

from freecell.GUI.scenes.menu_scene import MenuScene
from freecell.GUI.scenes.settings_scene import SettingsScene
from freecell.GUI.scenes.game_scene import GameScene


class FreeCellApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("FreeCell Solver GUI")
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()

        self.settings = load_settings()
        self.audio = AudioManager(self.settings)
        self.assets = AssetManager()

        self.running = True
        self.active_scene = None
        self.change_scene("menu")

    def change_scene(self, scene_name: str, *args) -> None:
        if scene_name == "menu":
            self.active_scene = MenuScene(
                self.screen, self.assets, self.audio, self.settings, self.change_scene
            )
        elif scene_name == "settings":
            self.active_scene = SettingsScene(
                self.screen, self.assets, self.audio, self.settings, self.change_scene
            )
        elif scene_name == "game":
            mode = args[0] if args else "manual"
            self.active_scene = GameScene(
                self.screen, self.assets, self.audio, self.settings, self.change_scene, mode=mode
            )

    def run(self) -> None:
        self.audio.play_music("menu")

        while self.running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            if self.active_scene:
                self.active_scene.handle_events(events)
                self.active_scene.render()

            pygame.display.flip()
            self.clock.tick(FPS)

        if isinstance(self.active_scene, GameScene):
            self.active_scene.solver_worker.stop()
            
        save_settings(self.settings)
        pygame.quit()


def run() -> None:
    freeze_support()
    app = FreeCellApp()
    app.run()
