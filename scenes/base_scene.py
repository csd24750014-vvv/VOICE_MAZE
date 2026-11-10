"""Shared visual shell and voice-message handling for full-screen scenes."""

from typing import TYPE_CHECKING, Optional

import pygame

from core.scene_manager import Scene
from ui.components import MicIndicator, Toast
from ui.theme import COLORS, draw_rounded_rect, draw_text, font
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
                            "I didn’t catch that. Try a short command.",
                            COLORS["yellow"],
                        )
                elif command.action == "cancel":
                    self.toast.show("Okay, I won’t do that.", COLORS["yellow"])
                else:
                    self.handle_command(command)
            elif message.kind == "unrecognized":
                self.toast.show("Say that again", COLORS["yellow"])
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
        draw_text(
            surface,
            title,
            (52, 57),
            size=34,
            color=COLORS["text"],
            role="heading",
        )
        draw_text(
            surface,
            subtitle,
            (54, 105),
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
            toast_width = min(460, width - 64)
            toast_rect = pygame.Rect(
                (width - toast_width) // 2,
                height - 112,
                toast_width,
                42,
            )
            self.toast.draw(surface, toast_rect)
