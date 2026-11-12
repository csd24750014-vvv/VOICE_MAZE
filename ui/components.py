"""Reusable interactive controls and information panels."""

import math
import time
from typing import Iterable, Optional, Sequence

import pygame

import config
from ui.theme import COLORS, draw_rounded_rect, draw_text, fit_text, font, wrap_text


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
        label_size = 19
        label_font = font(label_size, "heading")
        lines = wrap_text(self.label, label_font, max(1, self.rect.width - 32))
        while (
            len(lines) * (label_size + 3) > self.rect.height - 10
            and label_size > 12
        ):
            label_size -= 1
            label_font = font(label_size, "heading")
            lines = wrap_text(self.label, label_font, max(1, self.rect.width - 32))
        max_lines = max(1, (self.rect.height - 10) // (label_size + 3))
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = fit_text(
                lines[-1] + "...",
                label_font,
                max(1, self.rect.width - 32),
            )
        start_y = self.rect.centery - len(lines) * (label_size + 3) // 2
        for index, line in enumerate(lines):
            draw_text(
                surface,
                line,
                (self.rect.centerx, start_y + index * (label_size + 3)),
                size=label_size,
                color=label_color,
                role="heading",
                align="midtop",
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
        max_width = max(24, self.rect.width - 2 * padding)
        available_bottom = self.rect.bottom - padding
        if self.title:
            title_size = 22
            title_font = font(title_size, "heading")
            while title_size > 15 and title_font.size(self.title)[0] > max_width:
                title_size -= 1
                title_font = font(title_size, "heading")
            draw_text(
                surface,
                fit_text(self.title, title_font, max_width),
                (x, y),
                size=title_size,
                role="heading",
            )
            y += title_size + 16
        body_font = font(16)
        body_lines = [
            wrapped
            for line in self.body
            for wrapped in wrap_text(line, body_font, max_width)
        ]
        line_height = 22
        max_body_lines = max(0, (available_bottom - y) // line_height)
        if len(body_lines) > max_body_lines:
            body_lines = body_lines[:max_body_lines]
            if body_lines:
                body_lines[-1] = fit_text(
                    body_lines[-1] + "...",
                    body_font,
                    max_width,
                )
        previous_clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-8, -8))
        for line in body_lines:
            draw_text(surface, line, (x, y), size=16, color=COLORS["text_muted"])
            y += line_height
        surface.set_clip(previous_clip)


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
        "listening_offline": "Offline voice",
        "processing_offline": "Offline process",
        "listening_online": "Online voice",
        "processing_online": "Online process",
        "online_unavailable": "Internet unavailable",
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
        is_listening = self.status.startswith("listening")
        color_name = "red" if self.status in {"error", "online_unavailable"} else (
            "green" if is_listening else "cyan"
        )
        color = COLORS[color_name]
        draw_rounded_rect(surface, rect, COLORS["surface"], radius=14, border_color=COLORS["border"])
        center = (rect.x + 19, rect.centery)
        if is_listening:
            pulse = 3 + int((math.sin(current_time * 5.5) + 1) * 2)
            pygame.draw.circle(surface, (*color, 65), center, pulse + 5)
        pygame.draw.circle(surface, color, center, 5)
        draw_text(
            surface,
            fit_text(label, font(14), rect.width - 44),
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
        text_size = 15
        text_font = font(text_size)
        lines = wrap_text(self.message, text_font, rect.width - 30)
        while len(lines) > 2 and text_size > 11:
            text_size -= 1
            text_font = font(text_size)
            lines = wrap_text(self.message, text_font, rect.width - 30)
        max_lines = max(1, (rect.height - 12) // (text_size + 3))
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = fit_text(lines[-1] + "...", text_font, rect.width - 30)
        start_y = rect.centery - len(lines) * (text_size + 3) // 2
        previous_clip = surface.get_clip()
        surface.set_clip(rect.inflate(-8, -6))
        for index, line in enumerate(lines):
            draw_text(
                surface,
                line,
                (rect.centerx, start_y + index * (text_size + 3)),
                size=text_size,
                color=COLORS["text"],
                align="midtop",
            )
        surface.set_clip(previous_clip)


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
        button_rect = pygame.Rect(dialog.centerx - 90, dialog.bottom - 72, 180, 44)
        if self._button is None or self._button.rect != button_rect:
            self._button = Button(button_rect, self.button_label)
        title_font = font(26, "heading")
        draw_text(
            surface,
            fit_text(self.title, title_font, dialog.width - 56),
            (dialog.centerx, dialog.y + 32),
            26,
            role="heading",
            align="midtop",
        )
        body_font = font(16)
        body_width = dialog.width - 56
        body_lines = [
            wrapped
            for line in self.body
            for wrapped in wrap_text(line, body_font, body_width)
        ]
        line_height = 21
        body_y = dialog.y + 83
        max_lines = max(0, (button_rect.top - body_y - 10) // line_height)
        if len(body_lines) > max_lines:
            body_lines = body_lines[:max_lines]
            if body_lines:
                body_lines[-1] = fit_text(
                    body_lines[-1] + "...",
                    body_font,
                    body_width,
                )
        previous_clip = surface.get_clip()
        surface.set_clip(
            pygame.Rect(dialog.x + 20, body_y, dialog.width - 40, max(0, button_rect.top - body_y - 8))
        )
        y = body_y
        for line in body_lines:
            draw_text(surface, line, (dialog.x + 28, y), 16, COLORS["text_muted"])
            y += line_height
        surface.set_clip(previous_clip)
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

