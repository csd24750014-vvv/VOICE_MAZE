"""Animated entry screen with voice-controlled start, help, and quit actions."""

import math
import random
from typing import TYPE_CHECKING, List, Tuple

import pygame

from scenes.base_scene import BaseScene
from scenes.domain_scene import DomainScene
from ui.components import Button, Modal
from ui.theme import COLORS, draw_text
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class MenuScene(BaseScene):
    """Show the game title and its three accessible main-menu actions."""

    def __init__(self, game: "Game") -> None:
        """Create menu particles, mouse buttons, and the optional help dialog."""
        super().__init__(game)
        self._random = random.Random(21)
        self._particles: List[Tuple[float, float, float, float]] = [
            (
                self._random.random(),
                self._random.random(),
                self._random.uniform(8.0, 24.0),
                self._random.uniform(1.0, 3.0),
            )
            for _ in range(34)
        ]
        self._elapsed = 0.0
        self._buttons: List[Button] = []
        self._help: Modal | None = None

    def update(self, delta_seconds: float) -> None:
        """Animate ambient particles and process queued voice commands."""
        self._elapsed += delta_seconds
        super().update(delta_seconds)

    def handle_command(self, command: VoiceCommand) -> None:
        """Route the supported main-menu voice phrases."""
        if command.action == "start":
            self._open_domains()
        elif command.action == "how_to_play":
            self._show_help()
        elif command.action == "quit":
            self.game.running = False

    def handle_event(self, event: pygame.event.Event) -> None:
        """Respond to menu clicks and dismiss the help dialog with its button."""
        self._layout_buttons()
        if self._help is not None and self._help.visible:
            if self._help.handle_event(event, self.game.screen.get_rect()):
                self._help = None
            return
        for button in self._buttons:
            if button.handle_event(event):
                if button.label == "START LEARNING":
                    self._open_domains()
                elif button.label == "HOW TO PLAY":
                    self._show_help()
                else:
                    self.game.running = False
                return

    def draw(self, surface: pygame.Surface) -> None:
        """Render the animated welcome screen and persistent voice controls."""
        self._draw_ambient(surface)
        width, height = surface.get_size()
        draw_text(
            surface,
            "VOICE",
            (width // 2, height // 2 - 172),
            size=76,
            color=COLORS["text"],
            role="heading",
            align="midbottom",
        )
        draw_text(
            surface,
            "MAZE",
            (width // 2, height // 2 - 88),
            size=76,
            color=COLORS["cyan"],
            role="heading",
            align="midtop",
        )
        draw_text(
            surface,
            "Voice Controlled Gaming Tools for Enhanced Learning in the Skill Ecosystem",
            (width // 2, height // 2 + 5),
            size=17,
            color=COLORS["text_muted"],
            align="center",
        )
        draw_text(
            surface,
            "LEARN  →  PLAY  →  ASSESS  →  REVISE  →  UNLOCK",
            (width // 2, height // 2 + 45),
            size=15,
            color=COLORS["purple"],
            role="heading",
            align="center",
        )
        self._layout_buttons()
        for button in self._buttons:
            button.draw(surface)
        if self._help is not None:
            self._help.draw(surface)
        self.draw_shell(
            surface,
            "Your learning adventure",
            " ",
            "Speak naturally — for example, “start the game”, “show me how to play”, or “quit”.",
            draw_background=False,
        )

    def _layout_buttons(self) -> None:
        """Position the three menu actions relative to the current window size."""
        width, height = self.game.screen.get_size()
        center_x = width // 2
        start_y = height // 2 + 105
        labels = ("START LEARNING", "HOW TO PLAY", "QUIT GAME")
        accents = (COLORS["cyan"], COLORS["purple"], COLORS["pink"])
        if not self._buttons:
            self._buttons = [
                Button(
                    pygame.Rect(center_x - 154, start_y + index * 64, 308, 50),
                    label,
                    accent=accent,
                )
                for index, (label, accent) in enumerate(zip(labels, accents))
            ]
        else:
            for index, button in enumerate(self._buttons):
                button.rect = pygame.Rect(
                    center_x - 154,
                    start_y + index * 64,
                    308,
                    50,
                )

    def _draw_ambient(self, surface: pygame.Surface) -> None:
        """Draw the dark gradient and softly drift glowing menu particles."""
        self.draw_background(surface)
        width, height = surface.get_size()
        particle_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for index, (x_ratio, y_ratio, speed, radius) in enumerate(self._particles):
            y = (y_ratio * height - self._elapsed * speed) % height
            x = x_ratio * width + math.sin(self._elapsed * 0.45 + index) * 13
            color = COLORS["cyan"] if index % 2 == 0 else COLORS["purple"]
            pygame.draw.circle(
                particle_layer,
                (*color, 24),
                (int(x), int(y)),
                int(radius + (math.sin(self._elapsed + index) + 1)),
            )
            pygame.draw.circle(
                particle_layer,
                (*color, 75),
                (int(x), int(y)),
                max(1, int(radius / 3)),
            )
        surface.blit(particle_layer, (0, 0))

    def _open_domains(self) -> None:
        """Switch to the course-domain selection scene."""
        self.game.scenes.change(DomainScene(self.game))

    def _show_help(self) -> None:
        """Open concise instructions for mouse and spoken navigation."""
        self._help = Modal(
            "HOW TO PLAY",
            [
                "Choose a subject and difficulty, then read five short learning notes.",
                "Use your voice to navigate pages and move through the maze.",
                "Each locked door asks three questions from its topic.",
                "Miss a question set? Review that topic, then try the door again.",
                "Mouse controls are available whenever voice input is unavailable.",
            ],
            button_label="GOT IT",
        )
