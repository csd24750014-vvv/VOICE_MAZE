"""Shared visual shell and voice-message handling for full-screen scenes."""

from typing import TYPE_CHECKING, Optional

import pygame

from core.scene_manager import Scene
from ui.components import MicIndicator, Toast
from ui.theme import COLORS, draw_rounded_rect, draw_text, fit_text, font, wrap_text
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class BaseScene(Scene):
    """Provide shared background, microphone badge, captions, and toasts."""

    _background_cache: dict[tuple[int, int], pygame.Surface] = {}

    def __init__(self, game: "Game") -> None:
        """Set up shared scene presentation and a visible speech caption."""
        super().__init__(game)
        self.toast = Toast()
        self.caption = "Waiting for your first voice command"
        self.mic_indicator = MicIndicator()

    def update(self, delta_seconds: float) -> None:
        """Consume speech results without waiting on the microphone worker."""
        del delta_seconds
        self.game.voice_listener.set_command_context(self.command_context())
        for message in self.game.voice_listener.drain_messages():
            if message.kind == "recognized":
                self.caption = message.text
                command = self.game.command_parser.parse(
                    message.text,
                    context=self.command_context(),
                )
                if command is None:
                    if not self.game.command_parser.was_suppressed:
                        self.toast.show(
                            "I heard you, but that action is not available here. "
                            "Try one of the on-screen commands.",
                            COLORS["yellow"],
                        )
                elif command.action == "cancel":
                    self.toast.show("Okay, I won’t do that.", COLORS["yellow"])
                else:
                    self.handle_command(command)
            elif message.kind == "unrecognized":
                self.toast.show(message.text, COLORS["yellow"])
            elif message.kind == "notice":
                self.toast.show(message.text, COLORS["yellow"])
            else:
                self.toast.show(message.text, COLORS["red"])

    def command_context(self) -> Optional[str]:
        """Return a context hint for interpreting scene-specific speech."""
        return None

    def handle_command(self, command: VoiceCommand) -> None:
        """Handle a parsed command when a concrete scene supports it."""
        del command

    def draw_background(self, surface: pygame.Surface) -> None:
        """Paint a calm vertical dark gradient behind scene content."""
        size = surface.get_size()
        background = self._background_cache.get(size)
        if background is not None:
            surface.blit(background, (0, 0))
            return
        width, height = size
        top = COLORS["background"]
        bottom = (19, 20, 42)
        background = pygame.Surface(size)
        for y in range(height):
            ratio = y / max(1, height - 1)
            color = tuple(
                int(top[channel] + (bottom[channel] - top[channel]) * ratio)
                for channel in range(3)
            )
            pygame.draw.line(background, color, (0, y), (width, y))
        self._background_cache[size] = background
        surface.blit(background, (0, 0))

    def draw_shell(
        self,
        surface: pygame.Surface,
        section: str,
        title: str,
        subtitle: str,
        draw_background: bool = True,
    ) -> None:
        """Draw the shared background, page heading, microphone, and caption."""
        if draw_background:
            self.draw_background(surface)
        width, height = surface.get_size()
        draw_text(
            surface,
            section.upper(),
            (52, 33),
            size=13,
            color=COLORS["cyan"],
            role="heading",
        )
        title_font = font(34, "heading")
        title_size = 34
        title_width = width - 600
        while title_size > 23 and title_font.size(title)[0] > title_width:
            title_size -= 1
            title_font = font(title_size, "heading")
        draw_text(
            surface,
            fit_text(title, title_font, title_width),
            (52, 57),
            size=title_size,
            color=COLORS["text"],
            role="heading",
        )
        subtitle_width = width - 560
        subtitle_lines = wrap_text(subtitle, font(16), subtitle_width)[:2]
        if subtitle_lines:
            subtitle_lines[-1] = fit_text(
                subtitle_lines[-1] + ("..." if len(wrap_text(subtitle, font(16), subtitle_width)) > 2 else ""),
                font(16),
                subtitle_width,
            )
        for line_index, line in enumerate(subtitle_lines):
            draw_text(
                surface,
                line,
                (54, 104 + line_index * 19),
                size=16,
                color=COLORS["text_muted"],
            )
        self.mic_indicator.status = self.game.mic_status.state
        self.mic_indicator.draw(surface, pygame.Rect(width - 230, 32, 178, 42))

        footer = pygame.Rect(30, height - 57, width - 60, 38)
        caption = self.caption.replace("\n", " ").strip()
        mic_status = self.game.mic_status.snapshot()
        if mic_status.state == "error":
            status_width = min(390, max(280, width // 3))
            caption_width = footer.width - status_width - 12
            caption_rect = pygame.Rect(
                footer.x,
                footer.y,
                caption_width,
                footer.height,
            )
            status_rect = pygame.Rect(
                caption_rect.right + 12,
                footer.y,
                status_width,
                footer.height,
            )
            draw_rounded_rect(
                surface,
                status_rect,
                COLORS["surface"],
                radius=12,
                border_color=COLORS["red"],
            )
            notice = mic_status.message
            while notice and font(12).size(notice)[0] > status_rect.width - 24:
                notice = notice[:-4].rstrip() + "..."
            draw_text(
                surface,
                notice,
                (status_rect.x + 12, status_rect.centery),
                size=12,
                color=COLORS["red"],
                align="midleft",
            )
        else:
            caption_rect = footer
        draw_rounded_rect(
            surface,
            caption_rect,
            COLORS["surface"],
            radius=12,
            border_color=COLORS["border"],
        )
        max_caption_width = caption_rect.width - 30
        caption_font = font(14)
        while caption and caption_font.size(f"You said: {caption}")[0] > max_caption_width:
            caption = caption[:-4].rstrip() + "..."
        draw_text(
            surface,
            f"You said: {caption or '...'}",
            (caption_rect.x + 15, caption_rect.centery),
            size=14,
            color=COLORS["text_muted"],
            align="midleft",
        )
        if self.toast.visible:
            toast_width = min(420, width - 64)
            toast_rect = pygame.Rect(
                width - toast_width - 32,
                82,
                toast_width,
                52,
            )
            self.toast.draw(surface, toast_rect)
