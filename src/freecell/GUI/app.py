from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import freeze_support
from pathlib import Path
from typing import Iterable

import pygame

from freecell.GUI.move_adapter import get_legal_moves
from freecell.GUI.session import GameSession
from freecell.GUI.settings import GuiSettings, load_settings, save_settings
from freecell.GUI.solver_worker import SolverWorker
from freecell.core import Card, GameState, Move
from freecell.core.card import RANK_TO_NAME, SUITS

WINDOW_SIZE = (1200, 760)
FPS = 60
BG_COLOR = (18, 102, 62)
TEXT_COLOR = (245, 245, 245)
CARD_BG = (245, 245, 240)
CARD_BORDER = (35, 35, 35)
BUTTON_BG = (28, 52, 83)
BUTTON_ACTIVE = (50, 87, 130)
WARN_COLOR = (255, 216, 120)
ERROR_COLOR = (255, 160, 160)
SUCCESS_COLOR = (165, 235, 180)

SOLVER_MAX_EXPANSIONS = 50000

@dataclass(slots=True)
class Button:
    label: str
    rect: pygame.Rect


class AudioManager:
    def __init__(self, settings: GuiSettings) -> None:
        self.settings = settings
        self.assets_dir = Path(__file__).resolve().parent / "assets"
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


class FreeCellApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("FreeCell Solver GUI")
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("cambria", 46, bold=True)
        self.body_font = pygame.font.SysFont("consolas", 22)
        self.small_font = pygame.font.SysFont("consolas", 18)

        self.settings = load_settings()
        self.audio = AudioManager(self.settings)

        self.scene = "menu"
        self.mode = "manual"
        self.seed = 1
        self.session = GameSession.from_seed(self.seed)
        self.selected_source: tuple[str, int] | None = None
        self.message = ""
        self.message_color = TEXT_COLOR
        self.solver_worker = SolverWorker()
        self.solver_solution: tuple[Move, ...] = ()
        self.solver_solution_index = 0

    def run(self) -> None:
        running = True
        self.audio.play_music("menu")

        while running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False

            if self.scene == "menu":
                self._handle_menu(events)
                self._render_menu()
            elif self.scene == "settings":
                self._handle_settings(events)
                self._render_settings()
            else:
                self._poll_solver()
                self._handle_game(events)
                self._render_game()

            pygame.display.flip()
            self.clock.tick(FPS)

        self.solver_worker.stop()
        save_settings(self.settings)
        pygame.quit()

    def _set_message(self, text: str, color: tuple[int, int, int] = TEXT_COLOR) -> None:
        self.message = text
        self.message_color = color

    def _new_game(self, mode: str) -> None:
        self.mode = mode
        self.session = GameSession.from_seed(self.seed)
        self.selected_source = None
        self.solver_solution = ()
        self.solver_solution_index = 0
        self.solver_worker.stop()
        self.scene = "game"
        self.audio.play_music("game")

        if mode == "solver":
            self.solver_worker.start(
                self.session.state.to_packed(),
                self.settings.preferred_solver,
                SOLVER_MAX_EXPANSIONS,
            )

    def _poll_solver(self) -> None:
        if self.mode != "solver":
            return

        update = self.solver_worker.poll()
        if update.status == "running":
            self.last_solver_status = f"Solver running... {update.elapsed_seconds:.1f}s"
            return
        if update.status == "done":
            self.solver_solution = update.moves
            self.solver_solution_index = 0
            if update.solved:
                self._set_message(
                    f"Solver found solution: {len(update.moves)} moves, expanded {update.expanded_nodes}.",
                    SUCCESS_COLOR,
                )
            else:
                self._set_message(
                    "No solution found within current limit.",
                    WARN_COLOR,
                )

    def _buttons(self, definitions: Iterable[tuple[str, pygame.Rect]], events: list[pygame.event.Event]) -> str | None:
        clicked_pos: tuple[int, int] | None = None
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked_pos = event.pos
                break

        activated: str | None = None
        for label, rect in definitions:
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen, BUTTON_ACTIVE if hovered else BUTTON_BG, rect, border_radius=8)
            text = self.body_font.render(label, True, TEXT_COLOR)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)
            if clicked_pos is not None and rect.collidepoint(clicked_pos):
                activated = label
        return activated

    def _handle_menu(self, events: list[pygame.event.Event]) -> None:
        button = self._menu_buttons(events)
        if button == "Play Manual":
            self._new_game("manual")
        elif button == "Play Using Solver":
            self._new_game("solver")
        elif button == "Settings":
            self.scene = "settings"
        elif button == "Quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _menu_buttons(self, events: list[pygame.event.Event]) -> str | None:
        # Lấy tâm X của cửa sổ hiện tại
        center_x = self.screen.get_rect().centerx
        
        button_width = 260
        button_height = 52
        
        # Hàm phụ giúp tạo Rect tự động căn giữa theo trục X
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
        return self._buttons(defs, events)

    def _render_menu(self) -> None:
        self.screen.fill(BG_COLOR)
        
        # Lấy tâm X của cửa sổ hiện tại
        center_x = self.screen.get_rect().centerx
        
        title = self.title_font.render("FreeCell", True, TEXT_COLOR)
        
        # Tự động căn giữa text dựa vào center_x
        self.screen.blit(title, title.get_rect(center=(center_x, 140)))
        
        self._menu_buttons([])

    def _draw_slider(self, label: str, value: float | int, min_val: float | int, max_val: float | int, y_center: int) -> float | int:
        center_x = self.screen.get_rect().centerx

        # Định nghĩa chiều rộng của cả khối (Block Layout)
        # Label (180px) + Gap (20px) + Thanh trượt (200px) + Gap (20px) + Giá trị (60px) = Tổng 480px
        total_width = 480 
        start_x = center_x - (total_width // 2)

        # 1. Vẽ Label (chữ bên trái)
        label_surf = self.body_font.render(label, True, TEXT_COLOR)
        self.screen.blit(label_surf, label_surf.get_rect(midleft=(start_x, y_center)))

        # 2. Vẽ Track (đường ray thanh trượt)
        track_x = start_x + 200
        track_w = 200
        track_h = 10
        track_rect = pygame.Rect(track_x, y_center - track_h // 2, track_w, track_h)
        pygame.draw.rect(self.screen, BUTTON_BG, track_rect, border_radius=5)

        # 3. Tính toán vị trí và vẽ Cục nắm (Knob)
        ratio = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
        knob_x = track_x + int(ratio * track_w)

        # Vẽ phần ray đã được tô màu (tiến trình)
        fill_rect = pygame.Rect(track_x, y_center - track_h // 2, knob_x - track_x, track_h)
        pygame.draw.rect(self.screen, BUTTON_ACTIVE, fill_rect, border_radius=5)

        # Vẽ cục nắm
        knob_rect = pygame.Rect(0, 0, 16, 24)
        knob_rect.center = (knob_x, y_center)
        pygame.draw.rect(self.screen, TEXT_COLOR, knob_rect, border_radius=5)

        # 4. Vẽ Text hiển thị con số hiện tại bên phải
        val_str = f"{value:.2f}" if isinstance(value, float) and max_val <= 1.0 else f"{int(value)}"
        val_surf = self.body_font.render(val_str, True, WARN_COLOR)
        self.screen.blit(val_surf, val_surf.get_rect(midleft=(track_x + track_w + 20, y_center)))

        # 5. Xử lý logic kéo thả chuột
        mouse_x, mouse_y = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0] # Trạng thái chuột trái

        # Vùng click rộng hơn thanh ray một chút để dễ cầm nắm
        hitbox = track_rect.inflate(0, 30) 
        if mouse_pressed and hitbox.collidepoint(mouse_x, mouse_y):
            rel_x = max(0, min(mouse_x - track_x, track_w))
            new_ratio = rel_x / track_w
            new_val = min_val + new_ratio * (max_val - min_val)
            return type(value)(new_val) # Trả về đúng kiểu dữ liệu (float hoặc int)

        return value

    def _handle_settings(self, events: list[pygame.event.Event]) -> None:
        button = self._settings_buttons(events)
        if button == "Toggle Music Mute":
            self.settings.music_muted = not self.settings.music_muted
        elif button == "Toggle SFX Mute":
            self.settings.sfx_muted = not self.settings.sfx_muted
        elif button == "Back":
            save_settings(self.settings)
            self.audio.apply_settings()
            self.scene = "menu"

    def _settings_buttons(self, events: list[pygame.event.Event]) -> str | None:
        center_x = self.screen.get_rect().centerx
        
        # Nút Mute và Back cũng áp dụng quy tắc trừ đi một nửa width của chính nó
        defs = [
            ("Toggle Music Mute", pygame.Rect(center_x - 110, 420, 220, 44)),
            ("Toggle SFX Mute", pygame.Rect(center_x - 110, 480, 220, 44)),
            ("Back", pygame.Rect(center_x - 110, 560, 220, 50)),
        ]
        return self._buttons(defs, events)

    def _render_settings(self) -> None:
        self.screen.fill((22, 56, 80))
        center_x = self.screen.get_rect().centerx

        # Tiêu đề
        title = self.title_font.render("Settings", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(center_x, 120)))

        # Vẽ và cập nhật Slider (Tự động canh giữa hoàn hảo nhờ thuật toán Block Layout)
        self.settings.music_volume = self._draw_slider("Music Volume", self.settings.music_volume, 0.0, 1.0, 220)
        self.settings.sfx_volume = self._draw_slider("SFX Volume", self.settings.sfx_volume, 0.0, 1.0, 280)

        # Áp dụng ngay âm lượng mới nếu người dùng đang kéo slider
        self.audio.apply_settings()

        # Text phụ trợ
        info = self.small_font.render("Save is automatic when leaving this screen.", True, TEXT_COLOR)
        self.screen.blit(info, info.get_rect(center=(center_x, 650)))

        # Vẽ các nút Mute và Back
        self._settings_buttons([])

    def _handle_game(self, events: list[pygame.event.Event]) -> None:
        button = self._game_buttons(events)
        if button == "Menu":
            self.solver_worker.stop()
            self.scene = "menu"
            self.audio.play_music("menu")
            return
        if button == "Restart":
            self.session.restart()
            self.selected_source = None
            self.solver_solution = ()
            self.solver_solution_index = 0
            self.solver_worker.stop()
            self._set_message("Game restarted.")
            return
        if button == "Undo":
            if self.session.undo():
                self._set_message("Undo successful.")
        if button == "Redo":
            if self.session.redo():
                self._set_message("Redo successful.")

        board_click = None
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                board_click = event.pos
                break

        if board_click is not None:
            self._handle_board_click(board_click)

    def _apply_solver_step(self) -> bool:
        if self.solver_solution_index >= len(self.solver_solution):
            self._set_message("No solver move available.", WARN_COLOR)
            return False

        move = self.solver_solution[self.solver_solution_index]
        success, message = self.session.apply_move(move)
        if not success:
            self._set_message(f"Solver move failed: {message}", ERROR_COLOR)
            return False

        self.solver_solution_index += 1
        self._set_message(
            f"Applied solver step {self.solver_solution_index}/{len(self.solver_solution)}.",
            SUCCESS_COLOR,
        )
        return True

    def _game_buttons(self, events: list[pygame.event.Event]) -> str | None:
        defs = [
            ("Menu", pygame.Rect(40, 18, 120, 40)),
            ("Restart", pygame.Rect(175, 18, 120, 40)),
            ("Undo", pygame.Rect(310, 18, 120, 40)),
            ("Redo", pygame.Rect(445, 18, 120, 40)),
        ]
        return self._buttons(defs, events)

    def _handle_board_click(self, click_pos: tuple[int, int]) -> None:
        targets = self._board_targets()
        target = next((item for item in targets if item[2].collidepoint(click_pos)), None)
        if target is None:
            self.selected_source = None
            return

        pile_type, pile_index, _ = target
        if self.selected_source is None:
            if pile_type == "cascade" and self.session.state.cascade_top(pile_index) is not None:
                self.selected_source = (pile_type, pile_index)
                self._set_message(f"Selected cascade {pile_index}.")
            elif pile_type == "freecell" and self.session.state.freecells[pile_index] is not None:
                self.selected_source = (pile_type, pile_index)
                self._set_message(f"Selected freecell {pile_index}.")
            return

        source_type, source_index = self.selected_source
        destination_index = 0 if pile_type == "foundation" else pile_index
        move = Move(
            source=source_type,
            source_index=source_index,
            destination=pile_type,
            destination_index=destination_index,
            count=1,
        )

        legal_moves = get_legal_moves(self.session.state.to_packed())
        is_legal = any(
            candidate.source == move.source
            and candidate.source_index == move.source_index
            and candidate.destination == move.destination
            and candidate.destination_index == move.destination_index
            and candidate.count == move.count
            for candidate in legal_moves
        )
        if not is_legal:
            self._set_message("Illegal move.", ERROR_COLOR)
            self.audio.play_sfx("move_fail")
            self.selected_source = None
            return

        success, error = self.session.apply_move(move)
        if success:
            self._set_message("Move applied.", SUCCESS_COLOR)
            self.audio.play_sfx("move_ok")
            self.selected_source = None
            if self.session.state.is_victory:
                self.audio.play_music("win")
                self._set_message("Congratulations! You won!", SUCCESS_COLOR)
        else:
            self._set_message(f"Move failed: {error}", ERROR_COLOR)
            self.audio.play_sfx("move_fail")
            self.selected_source = None

    def _board_targets(self) -> list[tuple[str, int, pygame.Rect]]:
        targets: list[tuple[str, int, pygame.Rect]] = []
        freecell_start_x = 70
        for index in range(4):
            rect = pygame.Rect(freecell_start_x + index * 140, 120, 100, 140)
            targets.append(("freecell", index, rect))

        foundation_start_x = 670
        for index in range(4):
            rect = pygame.Rect(foundation_start_x + index * 120, 120, 100, 140)
            targets.append(("foundation", index, rect))

        cascade_start_x = 40
        for index in range(8):
            length = len(self.session.state.cascades[index])
            top_y = 300 if length == 0 else 300 + (length - 1) * 28
            rect = pygame.Rect(cascade_start_x + index * 145, top_y, 100, 140)
            targets.append(("cascade", index, rect))
        return targets

    def _render_card(self, rect: pygame.Rect, label: str, color: tuple[int, int, int], selected: bool = False) -> None:
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=10)
        pygame.draw.rect(self.screen, (247, 228, 140) if selected else CARD_BORDER, rect, width=3, border_radius=10)
        text = self.body_font.render(label, True, color)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _render_game(self) -> None:
        self.screen.fill(BG_COLOR)
        self._game_buttons([])

        header = self.small_font.render(
            f"Mode: {self.mode.upper()} | Moves {self.session.move_count} | Time {self.session.elapsed_seconds:.1f}s",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(header, (40, 70))

        # Freecells
        for index, card in enumerate(self.session.state.freecells):
            rect = pygame.Rect(40 + index * 140, 120, 100, 140)
            is_selected = self.selected_source == ("freecell", index)
            if card is None:
                pygame.draw.rect(self.screen, (25, 84, 56), rect, border_radius=10)
                pygame.draw.rect(self.screen, (190, 230, 204), rect, 2, border_radius=10)
                label = self.small_font.render(f"F{index}", True, TEXT_COLOR)
                self.screen.blit(label, (rect.x + 34, rect.y + 56))
            else:
                card_color = (196, 38, 38) if card.color == "red" else (20, 20, 20)
                self._render_card(rect, card.short_name, card_color, selected=is_selected)

        # Foundations
        for index, suit in enumerate(SUITS):
            rect = pygame.Rect(620 + index * 120, 120, 100, 140)
            rank = self.session.state.foundations[index]
            if rank == 0:
                pygame.draw.rect(self.screen, (25, 84, 56), rect, border_radius=10)
                pygame.draw.rect(self.screen, (190, 230, 204), rect, 2, border_radius=10)
                label = self.small_font.render(f"{suit} 0", True, TEXT_COLOR)
                self.screen.blit(label, (rect.x + 28, rect.y + 56))
            else:
                card = Card(rank=rank, suit=suit)
                card_color = (196, 38, 38) if card.color == "red" else (20, 20, 20)
                self._render_card(rect, card.short_name, card_color)

        # Cascades
        for index, cascade in enumerate(self.session.state.cascades):
            x = 40 + index * 145
            if not cascade:
                rect = pygame.Rect(x, 300, 100, 140)
                pygame.draw.rect(self.screen, (25, 84, 56), rect, border_radius=10)
                pygame.draw.rect(self.screen, (190, 230, 204), rect, 2, border_radius=10)
                label = self.small_font.render(f"C{index}", True, TEXT_COLOR)
                self.screen.blit(label, (rect.x + 30, rect.y + 56))
                continue

            for offset, card in enumerate(cascade):
                y = 300 + offset * 28
                rect = pygame.Rect(x, y, 100, 140)
                selected = self.selected_source == ("cascade", index) and offset == len(cascade) - 1
                card_color = (196, 38, 38) if card.color == "red" else (20, 20, 20)
                self._render_card(rect, card.short_name, card_color, selected=selected)

        if self.message:
            msg = self.body_font.render(self.message, True, self.message_color)
            self.screen.blit(msg, (40, 705))


def run() -> None:
    freeze_support()
    app = FreeCellApp()
    app.run()
