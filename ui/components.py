"""Reusable interactive controls and information panels."""

import math
import time
from typing import Iterable, Optional, Sequence

import pygame

import config
from ui.theme import COLORS, draw_rounded_rect, draw_text, font


class Button:
    """Rounded mouse button with an optional hover glow."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        accent: tuple[int, int, int] = COLORS["cyan"],
        enabled: bool = True,
    ) -> None:
        """Store the button's geometry, label, and interaction state."""
        self.rect = pygame.Rect(rect)
        self.label = label
        self.accent = accent
        self.enabled = enabled
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return true only when this enabled button receives a left click."""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if (
            self.enabled
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw a shadowed button and brighten it while the pointer hovers."""
        color = COLORS["surface_light"] if self.enabled else COLORS["surface"]
        if self.hovered and self.enabled:
            glow_rect = self.rect.inflate(10, 10)
            glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                glow,
                (*self.accent, 38),
                glow.get_rect(),
                border_radius=18,
            )
            surface.blit(glow, glow_rect.topleft)
            color = COLORS["surface_highlight"]
        shadow = self.rect.move(0, 5)
        pygame.draw.rect(surface, COLORS["black"], shadow, border_radius=14)
        draw_rounded_rect(
            surface,
            self.rect,
            color,
            radius=14,
            border_color=self.accent if self.hovered and self.enabled else COLORS["border"],
        )
        label_color = COLORS["text"] if self.enabled else COLORS["text_muted"]
        draw_text(
            surface,
            self.label,
            self.rect.center,
            size=19,
            color=label_color,
            role="heading",
            align="center",
        )


class Card:
    """Flexible rounded card for questions, notes, or menu groupings."""

    def __init__(
        self,
        rect: pygame.Rect,
        title: str = "",
        body: str | Sequence[str] = (),
        accent: tuple[int, int, int] = COLORS["purple"],
    ) -> None:
        """Keep card content and appearance together."""
        self.rect = pygame.Rect(rect)
        self.title = title
        self.body = [body] if isinstance(body, str) else list(body)
        self.accent = accent

    def draw(self, surface: pygame.Surface, padding: int = 24) -> None:
        """Draw the card, title, and readable wrapped body lines."""
        shadow = self.rect.move(0, 7)
        pygame.draw.rect(surface, COLORS["black"], shadow, border_radius=20)
        draw_rounded_rect(
            surface,
            self.rect,
            COLORS["surface"],
            radius=20,
            border_color=COLORS["border"],
        )
        pygame.draw.rect(
            surface,
            self.accent,
            pygame.Rect(self.rect.x + 1, self.rect.y + 18, 4, self.rect.height - 36),
            border_radius=3,
        )
        x = self.rect.x + padding
        y = self.rect.y + padding
        if self.title:
            draw_text(surface, self.title, (x, y), size=22, role="heading")
            y += 38
        for line in self.body:
            for wrapped in _wrap_text(line, max(24, self.rect.width - 2 * padding)):
                draw_text(surface, wrapped, (x, y), size=16, color=COLORS["text_muted"])
                y += 25


class ProgressBar:
    """Compact progress bar that safely handles empty or overfull progress."""

    def __init__(
        self,
        rect: pygame.Rect,
        value: float = 0,
        maximum: float = 100,
        accent: tuple[int, int, int] = COLORS["cyan"],
    ) -> None:
        """Store progress values and bar styling."""
        self.rect = pygame.Rect(rect)
        self.value = value
        self.maximum = maximum
        self.accent = accent

    @property
    def ratio(self) -> float:
        """Return progress clamped between zero and one."""
        if self.maximum <= 0:
            return 0.0
        return min(1.0, max(0.0, self.value / self.maximum))

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the muted track and its proportional colored fill."""
        pygame.draw.rect(surface, COLORS["surface_light"], self.rect, border_radius=8)
        fill_width = int(self.rect.width * self.ratio)
        if fill_width > 0:
            fill_rect = pygame.Rect(
                self.rect.x,
                self.rect.y,
                fill_width,
                self.rect.height,
            )
            pygame.draw.rect(surface, self.accent, fill_rect, border_radius=8)


class MicIndicator:
    """Persistent microphone status badge with a listening pulse."""

    STATUS_LABELS = {
        "listening": "Listening",
        "processing": "Processing",
        "error": "Mic unavailable",
        "idle": "Voice ready",
    }

    def __init__(self, status: str = "idle") -> None:
        """Initialize the indicator in a safe, non-error idle state."""
        self.status = status

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        now: Optional[float] = None,
    ) -> None:
        """Draw a status badge and pulse its dot while voice is listening."""
        current_time = time.monotonic() if now is None else now
        label = self.STATUS_LABELS.get(self.status, self.STATUS_LABELS["idle"])
        color_name = "red" if self.status == "error" else (
            "green" if self.status == "listening" else "cyan"
        )
        color = COLORS[color_name]
        draw_rounded_rect(surface, rect, COLORS["surface"], radius=14, border_color=COLORS["border"])
        center = (rect.x + 19, rect.centery)
        if self.status == "listening":
            pulse = 3 + int((math.sin(current_time * 5.5) + 1) * 2)
            pygame.draw.circle(surface, (*color, 65), center, pulse + 5)
        pygame.draw.circle(surface, color, center, 5)
        draw_text(
            surface,
            label,
            (rect.x + 32, rect.centery),
            size=14,
            color=COLORS["text"],
            align="midleft",
        )


class Toast:
    """Short-lived notification panel that never blocks the game loop."""

    def __init__(self, duration: float = config.TIMINGS["toast_seconds"]) -> None:
        """Prepare an empty toast with the chosen display duration."""
        self.duration = duration
        self.message = ""
        self.created_at = 0.0
        self.accent = COLORS["cyan"]

    @property
    def visible(self) -> bool:
        """Report whether a message is still within its display window."""
        return bool(self.message) and time.monotonic() - self.created_at < self.duration

    def show(
        self,
        message: str,
        accent: tuple[int, int, int] = COLORS["cyan"],
    ) -> None:
        """Start or restart the toast timer with a new message."""
        self.message = message
        self.created_at = time.monotonic()
        self.accent = accent

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw the toast only while its message remains current."""
        if not self.visible:
            return
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            panel,
            (*COLORS["surface"], 245),
            panel.get_rect(),
            border_radius=14,
        )
        surface.blit(panel, rect.topleft)
        draw_rounded_rect(surface, rect, COLORS["surface"], 14, self.accent, 2)
        draw_text(
            surface,
            self.message,
            rect.center,
            size=16,
            color=COLORS["text"],
            align="center",
        )


class Modal:
    """Centered dialog with clear content and a mouse-dismiss button."""

    def __init__(
        self,
        title: str,
        body: str | Iterable[str],
        button_label: str = "Continue",
    ) -> None:
        """Set the dialog text and its primary action label."""
        self.title = title
        self.body = [body] if isinstance(body, str) else list(body)
        self.button_label = button_label
        self.visible = True
        self._button: Optional[Button] = None

    def handle_event(self, event: pygame.event.Event, bounds: pygame.Rect) -> bool:
        """Return true when the dialog's primary mouse button is clicked."""
        dialog = self._dialog_rect(bounds)
        button_rect = pygame.Rect(dialog.centerx - 90, dialog.bottom - 72, 180, 44)
        if self._button is None or self._button.rect != button_rect:
            self._button = Button(button_rect, self.button_label)
        if self.visible and self._button.handle_event(event):
            self.visible = False
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Dim the screen and draw the modal dialog on top."""
        if not self.visible:
            return
        bounds = surface.get_rect()
        overlay = pygame.Surface(bounds.size, pygame.SRCALPHA)
        overlay.fill((4, 6, 14, 190))
        surface.blit(overlay, (0, 0))
        dialog = self._dialog_rect(bounds)
        draw_rounded_rect(
            surface,
            dialog,
            COLORS["surface"],
            radius=22,
            border_color=COLORS["border"],
            border_width=2,
        )
        draw_text(surface, self.title, (dialog.centerx, dialog.y + 32), 26, role="heading", align="midtop")
        y = dialog.y + 83
        for line in self.body:
            draw_text(surface, line, (dialog.x + 28, y), 16, COLORS["text_muted"])
            y += 27
        button_rect = pygame.Rect(dialog.centerx - 90, dialog.bottom - 72, 180, 44)
        if self._button is None or self._button.rect != button_rect:
            self._button = Button(button_rect, self.button_label)
        self._button.draw(surface)

    @staticmethod
    def _dialog_rect(bounds: pygame.Rect) -> pygame.Rect:
        """Return a centered dialog rectangle that fits the current window."""
        width = min(620, bounds.width - 64)
        height = min(400, bounds.height - 64)
        return pygame.Rect(0, 0, width, height).move(
            bounds.centerx - width // 2,
            bounds.centery - height // 2,
        )


def _wrap_text(text: str, max_width: int) -> list[str]:
    """Wrap a string into lines that fit within the requested pixel width."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font(16).size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines
