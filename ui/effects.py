"""Reusable glow and motion effects for the game interface."""

import math

import pygame


def draw_glow(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    max_alpha: int = 72,
    layers: int = 4,
) -> None:
    """Draw a soft concentric glow onto a transparent effect layer."""
    if radius <= 0 or layers <= 0 or not 0 <= max_alpha <= 255:
        raise ValueError("Glow radius, layers, and alpha must be within valid ranges.")
    for layer in range(layers, 0, -1):
        glow_radius = radius + round(radius * layer / layers)
        alpha = max(1, round(max_alpha * (layers - layer + 1) / layers))
        pygame.draw.circle(surface, (*color, alpha), center, glow_radius)


def screen_shake_offset(
    elapsed_seconds: float,
    duration_seconds: float = 0.18,
    intensity: float = 5.0,
) -> tuple[int, int]:
    """Return a short, decaying shake offset or no offset after its duration."""
    if elapsed_seconds < 0 or duration_seconds <= 0 or intensity < 0:
        raise ValueError("Shake time and intensity must be non-negative.")
    if elapsed_seconds >= duration_seconds or intensity == 0:
        return (0, 0)
    remaining = 1.0 - elapsed_seconds / duration_seconds
    return (
        round(math.sin(elapsed_seconds * 71.0) * intensity * remaining),
        round(math.cos(elapsed_seconds * 59.0) * intensity * remaining),
    )
