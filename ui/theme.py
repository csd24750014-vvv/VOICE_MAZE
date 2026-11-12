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


def wrap_text(
    text: str,
    text_font: pygame.font.Font,
    max_width: int,
) -> list[str]:
    """Wrap words to a pixel width and split unbroken tokens when required."""
    if max_width <= 0:
        return [""]
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if text_font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            while text_font.size(word)[0] > max_width:
                part = ""
                for character in word:
                    if part and text_font.size(part + character)[0] > max_width:
                        lines.append(part)
                        part = character
                    else:
                        part += character
                word = part
            current = word
        lines.append(current)
    return lines


def fit_text(
    text: str,
    text_font: pygame.font.Font,
    max_width: int,
) -> str:
    """Shorten one-line text with an ellipsis until it fits its pixel width."""
    if max_width <= 0:
        return ""
    if text_font.size(text)[0] <= max_width:
        return text
    shortened = text.rstrip()
    while shortened and text_font.size(shortened + "...")[0] > max_width:
        shortened = shortened[:-1].rstrip()
    return shortened + "..." if shortened else ""


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
