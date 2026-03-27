import pygame
from typing import Iterable

from freecell.GUI.core.constants import BUTTON_BG, BUTTON_ACTIVE, TEXT_COLOR, WARN_COLOR, CARD_BG, CARD_BORDER
from freecell.GUI.managers.assets import AssetManager

def draw_buttons(screen: pygame.Surface, font: pygame.font.Font, definitions: Iterable[tuple[str, pygame.Rect]], events: list[pygame.event.Event]) -> str | None:
    clicked_pos: tuple[int, int] | None = None
    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked_pos = event.pos
            break

    activated: str | None = None
    for label, rect in definitions:
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, BUTTON_ACTIVE if hovered else BUTTON_BG, rect, border_radius=8)
        text = font.render(label, True, TEXT_COLOR)
        text_rect = text.get_rect(center=rect.center)
        screen.blit(text, text_rect)
        if clicked_pos is not None and rect.collidepoint(clicked_pos):
            activated = label
    return activated

def draw_slider(screen: pygame.Surface, font: pygame.font.Font, label: str, value: float | int, min_val: float | int, max_val: float | int, y_center: int) -> float | int:
    center_x = screen.get_rect().centerx
    total_width = 480 
    start_x = center_x - (total_width // 2)

    label_surf = font.render(label, True, TEXT_COLOR)
    screen.blit(label_surf, label_surf.get_rect(midleft=(start_x, y_center)))

    track_x = start_x + 200
    track_w = 200
    track_h = 10
    track_rect = pygame.Rect(track_x, y_center - track_h // 2, track_w, track_h)
    pygame.draw.rect(screen, BUTTON_BG, track_rect, border_radius=5)

    ratio = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
    knob_x = track_x + int(ratio * track_w)

    fill_rect = pygame.Rect(track_x, y_center - track_h // 2, knob_x - track_x, track_h)
    pygame.draw.rect(screen, BUTTON_ACTIVE, fill_rect, border_radius=5)

    knob_rect = pygame.Rect(0, 0, 16, 24)
    knob_rect.center = (knob_x, y_center)
    pygame.draw.rect(screen, TEXT_COLOR, knob_rect, border_radius=5)

    val_str = f"{value:.2f}" if isinstance(value, float) and max_val <= 1.0 else f"{int(value)}"
    val_surf = font.render(val_str, True, WARN_COLOR)
    screen.blit(val_surf, val_surf.get_rect(midleft=(track_x + track_w + 20, y_center)))

    mouse_x, mouse_y = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    
    hitbox = track_rect.inflate(0, 30) 
    if mouse_pressed and hitbox.collidepoint(mouse_x, mouse_y):
        rel_x = max(0, min(mouse_x - track_x, track_w))
        new_ratio = rel_x / track_w
        new_val = min_val + new_ratio * (max_val - min_val)
        return type(value)(new_val)

    return value

def draw_card(screen: pygame.Surface, font: pygame.font.Font, assets: AssetManager, rect: pygame.Rect, label: str, color: tuple[int, int, int], selected: bool = False) -> None:
    if label in assets.card_images:
        screen.blit(assets.card_images[label], rect.topleft)
        if selected:
            pygame.draw.rect(screen, (247, 228, 140), rect, width=4, border_radius=10)
    else:
        pygame.draw.rect(screen, CARD_BG, rect, border_radius=10)
        pygame.draw.rect(screen, (247, 228, 140) if selected else CARD_BORDER, rect, width=3, border_radius=10)
        text = font.render(label, True, color)
        screen.blit(text, text.get_rect(center=rect.center))
