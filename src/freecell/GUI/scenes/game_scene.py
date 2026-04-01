import pygame
from freecell.GUI.scenes.base_scene import BaseScene
from freecell.GUI.core.constants import BG_COLOR, TEXT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARN_COLOR, SOLVER_MAX_EXPANSIONS, WINDOW_SIZE, BUTTON_BG, CASCADE_OFFSET
from freecell.GUI.ui.components import draw_buttons, draw_card
from freecell.GUI.core.session import GameSession
from freecell.GUI.core.solver_worker import SolverWorker
from freecell.core import Move, Card
from freecell.core.card import SUITS

class GameScene(BaseScene):
    def __init__(self, screen, assets, audio, settings, change_scene, mode: str = "manual"):
        super().__init__(screen, assets, audio, settings, change_scene)
        self.mode = mode
        self.seed = 1
        self.session = GameSession.from_seed(self.seed)
        self.selected_source: tuple[str, int] | None = None
        self.drag_count = 1
        self.message = ""
        self.message_color = TEXT_COLOR
        self.solver_worker = SolverWorker()
        self.solver_solution: tuple[Move, ...] = ()
        self.solver_solution_index = 0
        self.show_solver_popup = False
        self.solver_choices = ["BFS", "DFS", "UCS", "A*"]
        try:
            self.solver_choice_index = self.solver_choices.index(self.settings.preferred_solver)
        except Exception:
            self.solver_choice_index = 0

        self.is_dragging = False
        self.drag_offset = (0, 0)
        self.drag_pos = (0, 0)
        self.auto_run_solution = False
        self._auto_phase = ""
        self._auto_phase_end = 0.0

        if self.mode == "solver":
            self.solver_worker.start(
                self.session.state.to_packed(),
                self.settings.preferred_solver,
                SOLVER_MAX_EXPANSIONS,
            )

    def _set_message(self, text: str, color: tuple[int, int, int] = TEXT_COLOR) -> None:
        self.message = text
        self.message_color = color

    def _poll_solver(self) -> None:
        if self.mode != "solver":
            return

        update = self.solver_worker.poll()
        if update.status == "running":
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

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        self._poll_solver()
        button = self._game_buttons(events)
        if button == "Solver":
            # show solver popup to choose solver and start/quit
            self.show_solver_popup = True
            return

        # If popup is shown, let it consume events first
        if self.show_solver_popup:
            self._handle_solver_popup_events(events)
            return
        if button == "Next Step":
            if self.auto_run_solution:
                self._set_message("Disabled during auto-run.", WARN_COLOR)
            else:
                self._apply_solver_step()
        if button == "Auto Run":
            # do nothing if there's no prepared solution or solver is still running
            if not self.solver_solution or self.solver_worker.is_running:
                self._set_message("No solver solution available.", WARN_COLOR)
                return
            # toggle auto-run: will wait 1s before applying a step, then pause 0.5s
            if self.auto_run_solution:
                self.auto_run_solution = False
                self._set_message("Auto-run stopped.")
            else:
                self.auto_run_solution = True
                self._auto_phase = "wait_before_apply"
                self._auto_phase_end = pygame.time.get_ticks() / 1000.0 + 1.0
                # disable any current drag/selection
                self.selected_source = None
                self.is_dragging = False
                self._set_message("Auto-run started.")
            return

        if button == "Menu":
            # TODO: save current session state for potential resume
            self.solver_worker.stop()
            self.change_scene("menu")
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

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_w:
                from freecell.core.state import GameState
                foundations = (13, 13, 13, 12)
                freecells = (Card(rank=13, suit='S'), None, None, None)
                cascades = ((), (), (), (), (), (), (), ())
                self.session.state = GameState(cascades=cascades, freecells=freecells, foundations=foundations)
                self.session._history.append(self.session.state)
                self.session._cursor = len(self.session._history) - 1
                self._set_message("TEST MODE: Move K S to Foundation to Win!")

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_mouse_down(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mouse_motion(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._handle_mouse_up(event.pos)

        # Auto-run processing: non-blocking timer-driven step application
        if self.auto_run_solution:
            now = pygame.time.get_ticks() / 1000.0
            if self._auto_phase == "wait_before_apply" and now >= self._auto_phase_end:
                ok = self._apply_solver_step()
                if not ok:
                    self.auto_run_solution = False
                    self._set_message("Auto-run finished.")
                else:
                    self._auto_phase = "pause_after_apply"
                    self._auto_phase_end = now + 0.2
            elif self._auto_phase == "pause_after_apply" and now >= self._auto_phase_end:
                self._auto_phase = "wait_before_apply"
                self._auto_phase_end = now + 0.8

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

    def _handle_mouse_down(self, mouse_pos: tuple[int, int]) -> None:
        if self.session.state.is_victory:
            return
        if self.auto_run_solution:
            return
            
        targets = self._board_targets()
        target = next((item for item in targets if item[2].collidepoint(mouse_pos)), None)

        if target is None:
            self.selected_source = None
            return

        pile_type, pile_index, rect = target

        if self.selected_source and self.selected_source != (pile_type, pile_index):
            self._attempt_move(self.selected_source, (pile_type, pile_index))
            return

        if pile_type == "cascade" and self.session.state.cascade_top(pile_index) is not None:
            cascade = self.session.state.cascades[pile_index]
            clicked_offset = len(cascade) - 1
            for offset in range(len(cascade) - 1, -1, -1):
                card_y = 300 + offset * CASCADE_OFFSET
                card_rect = pygame.Rect(rect.x, card_y, 100, 140 if offset == len(cascade) - 1 else CASCADE_OFFSET)
                if card_rect.collidepoint(mouse_pos):
                    clicked_offset = offset
                    break
            
            from freecell.core.rules import is_descending_alternating
            stack_to_drag = cascade[clicked_offset:]
            if is_descending_alternating(stack_to_drag):
                self.selected_source = (pile_type, pile_index)
                self.drag_count = len(stack_to_drag)
                self.is_dragging = True
                self.drag_offset = (mouse_pos[0] - rect.x, mouse_pos[1] - (300 + clicked_offset * CASCADE_OFFSET))
                self.drag_pos = mouse_pos
                self._set_message(f"Selected cascade {pile_index} ({self.drag_count} cards).")
            else:
                self._set_message("Invalid stack selection.", ERROR_COLOR)
            
        elif pile_type == "freecell" and self.session.state.freecells[pile_index] is not None:
            self.selected_source = (pile_type, pile_index)
            self.drag_count = 1
            self.is_dragging = True
            self.drag_offset = (mouse_pos[0] - rect.x, mouse_pos[1] - rect.y)
            self.drag_pos = mouse_pos
            self._set_message(f"Selected freecell {pile_index}.")

        elif pile_type == "foundation" and self.session.state.foundations[pile_index] > 0:
            self.selected_source = (pile_type, pile_index)
            self.drag_count = 1
            self.is_dragging = True
            self.drag_offset = (mouse_pos[0] - rect.x, mouse_pos[1] - rect.y)
            self.drag_pos = mouse_pos
            self._set_message(f"Selected foundation {pile_index}.")

    def _handle_mouse_motion(self, mouse_pos: tuple[int, int]) -> None:
        if self.auto_run_solution:
            return
        if self.is_dragging:
            self.drag_pos = mouse_pos

    def _handle_mouse_up(self, mouse_pos: tuple[int, int]) -> None:
        if self.auto_run_solution:
            return

        if not self.is_dragging:
            return

        self.is_dragging = False
        targets = self._board_targets()
        target = next((item for item in targets if item[2].collidepoint(mouse_pos)), None)

        if target is None:
            self.selected_source = None
            return

        dest_type, dest_index, _ = target

        if self.selected_source == (dest_type, dest_index):
            return

        self._attempt_move(self.selected_source, (dest_type, dest_index))

    def _attempt_move(self, source: tuple[str, int], dest: tuple[str, int]) -> None:
        source_type, source_index = source
        dest_type, dest_index = dest
        destination_index = 0 if dest_type == "foundation" else dest_index

        move = Move(
            source=source_type, source_index=source_index,
            destination=dest_type, destination_index=destination_index,
            count=self.drag_count,
        )

        success, error = self.session.apply_move(move)
        if not success:
            self._set_message(f"Illegal move: {error}", ERROR_COLOR)
            self.audio.play_sfx("move_fail")
            self.selected_source = None
            return

        self._set_message("Move applied.", SUCCESS_COLOR)
        self.audio.play_sfx("move_ok")
        self.selected_source = None
        if self.session.state.is_victory:
            self.audio.play_music("win")
            self._set_message("Congratulations! You won!", SUCCESS_COLOR)

    def _game_buttons(self, events: list[pygame.event.Event]) -> str | None:
        defs = [
            ("Menu", pygame.Rect(40, 18, 120, 40)),
            ("Restart", pygame.Rect(175, 18, 120, 40)),
            ("Undo", pygame.Rect(310, 18, 120, 40)),
            ("Redo", pygame.Rect(445, 18, 120, 40)),
            ("Solver", pygame.Rect(580, 18, 120, 40)), # choose BFS, DFS, A*, UCS
            ("Next Step", pygame.Rect(715, 18, 120, 40)), # step through solver solution
            ("Auto Run", pygame.Rect(850, 18, 120, 40)) # Disable manual card move.
        ]
        return draw_buttons(self.screen, self.assets.body_font, defs, events)

    def _handle_solver_popup_events(self, events: list[pygame.event.Event]) -> None:
        center_x = self.screen.get_rect().centerx
        center_y = self.screen.get_rect().centery + 35
        popup_rect = pygame.Rect(0, 0, 360, 180)
        popup_rect.center = (center_x, center_y)

        dropdown_rect = pygame.Rect(popup_rect.x + 40, popup_rect.y + 50, popup_rect.width - 80, 40)
        solve_rect = pygame.Rect(popup_rect.x + 60, popup_rect.y + 110, 100, 36)
        quit_rect = pygame.Rect(popup_rect.x + 200, popup_rect.y + 110, 100, 36)

        # handle dropdown click (cycle options)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if dropdown_rect.collidepoint(event.pos):
                    self.solver_choice_index = (self.solver_choice_index + 1) % len(self.solver_choices)
                    return

        # handle popup buttons
        defs = [("Solve", solve_rect), ("Quit", quit_rect)]
        clicked = draw_buttons(self.screen, self.assets.body_font, defs, events)
        if clicked == "Solve":
            solver_name = self.solver_choices[self.solver_choice_index]
            self.settings.preferred_solver = solver_name
            self.solver_worker.start(self.session.state.to_packed(), solver_name, SOLVER_MAX_EXPANSIONS)
            self.show_solver_popup = False
            self._set_message(f"Started solver: {solver_name}.")
        elif clicked == "Quit":
            self.solver_worker.stop()
            self.show_solver_popup = False
            self._set_message("Solver stopped.")

    def _render_solver_popup(self) -> None:
        center_x = self.screen.get_rect().centerx
        center_y = self.screen.get_rect().centery + 35
        overlay = pygame.Surface((WINDOW_SIZE[0], WINDOW_SIZE[1] - 70), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 70))

        popup_rect = pygame.Rect(0, 0, 360, 180)
        popup_rect.center = (center_x, center_y)
        pygame.draw.rect(self.screen, BUTTON_BG, popup_rect, border_radius=12)
        pygame.draw.rect(self.screen, TEXT_COLOR, popup_rect, width=2, border_radius=12)

        title = self.assets.title_font.render("Solver", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(center_x, popup_rect.y + 24)))

        dropdown_rect = pygame.Rect(popup_rect.x + 40, popup_rect.y + 50, popup_rect.width - 80, 40)
        pygame.draw.rect(self.screen, (40, 40, 40), dropdown_rect, border_radius=6)
        pygame.draw.rect(self.screen, (160, 160, 160), dropdown_rect, width=2, border_radius=6)
        current = self.solver_choices[self.solver_choice_index]
        label = self.assets.body_font.render(f"{current}  (click to change)", True, TEXT_COLOR)
        self.screen.blit(label, (dropdown_rect.x + 8, dropdown_rect.y + 8))

        # Draw buttons
        solve_rect = pygame.Rect(popup_rect.x + 60, popup_rect.y + 110, 100, 36)
        quit_rect = pygame.Rect(popup_rect.x + 200, popup_rect.y + 110, 100, 36)
        defs = [("Solve", solve_rect), ("Quit", quit_rect)]
        draw_buttons(self.screen, self.assets.body_font, defs, [])

    def _board_targets(self) -> list[tuple[str, int, pygame.Rect]]:
        targets: list[tuple[str, int, pygame.Rect]] = []
        for index in range(4):
            rect = pygame.Rect(60 + index * 140, 120, 100, 140)
            targets.append(("freecell", index, rect))

        for index in range(4):
            rect = pygame.Rect(60 + (index + 4) * 140, 120, 100, 140)
            targets.append(("foundation", index, rect))

        for index in range(8):
            length = len(self.session.state.cascades[index])
            height = 140 if length == 0 else 140 + (length - 1) * CASCADE_OFFSET
            rect = pygame.Rect(60 + index * 140, 300, 100, height)
            targets.append(("cascade", index, rect))
        return targets

    def render(self) -> None:
        self.screen.fill(BG_COLOR)
        self._game_buttons([])

        header = self.assets.small_font.render(
            f"Mode: {self.mode.upper()} | Moves {self.session.move_count} | Time {self.session.elapsed_seconds:.1f}s",
            True, TEXT_COLOR,
        )
        self.screen.blit(header, (40, 70))

        dragged_cards = []

        # Freecells
        for index, card in enumerate(self.session.state.freecells):
            rect = pygame.Rect(60 + index * 140, 120, 100, 140)
            is_selected = self.selected_source == ("freecell", index)
            if card is None:
                pygame.draw.rect(self.screen, (25, 84, 56), rect, border_radius=10)
                pygame.draw.rect(self.screen, (190, 230, 204), rect, 2, border_radius=10)
                label = self.assets.small_font.render(f"F{index}", True, TEXT_COLOR)
                self.screen.blit(label, (rect.x + 34, rect.y + 56))
            else:
                if self.is_dragging and is_selected:
                    dragged_cards.append(card)
                    pygame.draw.rect(self.screen, (25, 84, 56), rect, border_radius=10)
                    pygame.draw.rect(self.screen, (190, 230, 204), rect, 2, border_radius=10)
                else:
                    card_color = (196, 38, 38) if card.color == "red" else (20, 20, 20)
                    draw_card(self.screen, self.assets.body_font, self.assets, rect, card.short_name, card_color, selected=is_selected)

        # Foundations
        for index, suit in enumerate(SUITS):
            rect = pygame.Rect(60 + (index + 4) * 140, 120, 100, 140)
            rank = self.session.state.foundations[index]
            is_selected = self.selected_source == ("foundation", index)
            
            draw_rank = rank - 1 if (self.is_dragging and is_selected) else rank

            if draw_rank == 0:
                pygame.draw.rect(self.screen, (25, 84, 56), rect, border_radius=10)
                pygame.draw.rect(self.screen, (190, 230, 204), rect, 2, border_radius=10)
                label = self.assets.small_font.render(f"{suit} 0", True, TEXT_COLOR)
                self.screen.blit(label, (rect.x + 28, rect.y + 56))
            else:
                card = Card(rank=draw_rank, suit=suit)
                card_color = (196, 38, 38) if card.color == "red" else (20, 20, 20)
                draw_card(self.screen, self.assets.body_font, self.assets, rect, card.short_name, card_color)

            if self.is_dragging and is_selected:
                dragged_cards.append(Card(rank=rank, suit=suit))

        # Cascades
        for index, cascade in enumerate(self.session.state.cascades):
            x = 60 + index * 140
            if not cascade:
                rect = pygame.Rect(x, 300, 100, 140)
                pygame.draw.rect(self.screen, (25, 84, 56), rect, border_radius=10)
                pygame.draw.rect(self.screen, (190, 230, 204), rect, 2, border_radius=10)
                label = self.assets.small_font.render(f"C{index}", True, TEXT_COLOR)
                self.screen.blit(label, (rect.x + 30, rect.y + 56))
                continue

            for offset, card in enumerate(cascade):
                y = 300 + offset * CASCADE_OFFSET
                rect = pygame.Rect(x, y, 100, 140)
                selected = self.selected_source == ("cascade", index) and offset >= len(cascade) - self.drag_count
                
                if self.is_dragging and selected:
                    dragged_cards.append(card)
                    continue

                card_color = (196, 38, 38) if card.color == "red" else (20, 20, 20)
                draw_card(self.screen, self.assets.body_font, self.assets, rect, card.short_name, card_color, selected=selected)

        # Draw dragged cards overlay
        if self.is_dragging and dragged_cards:
            drag_x = self.drag_pos[0] - self.drag_offset[0]
            drag_y = self.drag_pos[1] - self.drag_offset[1]
            for offset, card in enumerate(dragged_cards):
                drag_rect = pygame.Rect(drag_x, drag_y + offset * CASCADE_OFFSET, 100, 140)
                card_color = (196, 38, 38) if card.color == "red" else (20, 20, 20)
                draw_card(self.screen, self.assets.body_font, self.assets, drag_rect, card.short_name, card_color, selected=True)

        # Messages
        if self.message:
            msg = self.assets.body_font.render(self.message, True, self.message_color)
            self.screen.blit(msg, (40, 705))
        
        # Solver popup
        if self.show_solver_popup:
            self._render_solver_popup()
            
        # Victory Overlay
        if self.session.state.is_victory:
            overlay = pygame.Surface((WINDOW_SIZE[0], WINDOW_SIZE[1] - 70), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 70))
            
            center_x = self.screen.get_rect().centerx
            center_y = self.screen.get_rect().centery + 35
            popup_rect = pygame.Rect(0, 0, 480, 220)
            popup_rect.center = (center_x, center_y)
            pygame.draw.rect(self.screen, BUTTON_BG, popup_rect, border_radius=15)
            pygame.draw.rect(self.screen, SUCCESS_COLOR, popup_rect, width=5, border_radius=15)
            
            title = self.assets.title_font.render("VICTORY!", True, SUCCESS_COLOR)
            self.screen.blit(title, title.get_rect(center=(center_x, center_y - 45)))
            
            stats = self.assets.body_font.render(f"Moves: {self.session.move_count}    Time: {self.session.elapsed_seconds:.1f}s", True, TEXT_COLOR)
            self.screen.blit(stats, stats.get_rect(center=(center_x, center_y + 15)))
            
            instruction = self.assets.small_font.render("Click 'Restart' or 'Menu' to play again", True, WARN_COLOR)
            self.screen.blit(instruction, instruction.get_rect(center=(center_x, center_y + 60)))
