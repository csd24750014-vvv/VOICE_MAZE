"""Shared color, spacing, and typography helpers for the game interface."""

from functools import lru_cache

import pygame

import config

COLORS = config.COLORS
SPACING = {
    "xs": 6,
    "sm": 12,
    "md": 20,
    "lg": 30,
    "xl": 44,
}


@lru_cache(maxsize=32)
def font(size: int, role: str = "body") -> pygame.font.Font:
    """Return a cached system font for the requested size and visual role."""
    if not pygame.font.get_init():
        pygame.font.init()
    family = config.FONTS.get(role, config.FONTS["body"])
    return pygame.font.SysFont(family, size, bold=role == "heading")


def draw_text(
    surface: pygame.Surface,
    text: str,
    position: tuple[int, int],
    size: int = 18,
    color: tuple[int, int, int] = COLORS["text"],
    role: str = "body",
    align: str = "topleft",
) -> pygame.Rect:
    """Render a text label at a named anchor and return its resulting bounds."""
    rendered = font(size, role).render(text, True, color)
    bounds = rendered.get_rect()
    setattr(bounds, align, position)
    surface.blit(rendered, bounds)
    return bounds


def draw_rounded_rect(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    radius: int = 16,
    border_color: tuple[int, int, int] | None = None,
    border_width: int = 1,
) -> None:
    """Draw a rounded panel, optionally with a thin outline."""
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color is not None:
        pygame.draw.rect(
            surface,
            border_color,
            rect,
            width=border_width,
            border_radius=radius,
        )
