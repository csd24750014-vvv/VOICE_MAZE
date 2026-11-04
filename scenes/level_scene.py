"""Difficulty selection screen for the selected learning domain."""

from typing import TYPE_CHECKING

import pygame

from scenes.base_scene import BaseScene
from scenes.notes_scene import NotesScene
from ui.components import Button, Card
from ui.theme import COLORS, draw_text
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class LevelScene(BaseScene):
    """Let the learner select beginner, intermediate, or advanced content."""

    LEVELS = ("Beginner", "Intermediate", "Advanced")
    DESCRIPTIONS = (
        "Core ideas, gentle pace",
        "Connected concepts, more practice",
        "Deeper applications and challenges",
    )
    ACCENTS = (COLORS["green"], COLORS["cyan"], COLORS["purple"])

    def __init__(self, game: "Game") -> None:
        """Create difficulty controls for the currently selected subject."""
        super().__init__(game)
        self._buttons: list[Button] = []
        self._back_button = Button(pygame.Rect(0, 0, 150, 44), "BACK", COLORS["text_muted"])

    def handle_command(self, command: VoiceCommand) -> None:
        """Open the chosen difficulty or return to the domain screen."""
        if command.action == "select_level" and command.value in self.LEVELS:
            self._select_level(command.value)
        elif command.action == "back":
            from scenes.domain_scene import DomainScene

            self.game.scenes.change(DomainScene(self.game))

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle mouse difficulty selection and the back control."""
        self._layout_buttons()
        if self._back_button.handle_event(event):
            from scenes.domain_scene import DomainScene

            self.game.scenes.change(DomainScene(self.game))
            return
        for button, level in zip(self._buttons, self.LEVELS):
            if button.handle_event(event):
                self._select_level(level)
                return

    def draw(self, surface: pygame.Surface) -> None:
        """Display the available difficulties and their learning pace."""
        domain = self.game.state.domain or "your chosen domain"
        self.draw_shell(
            surface,
            "Step 2 of 3",
            "Set your challenge level",
            f"{domain}  •  Say “beginner”, “medium”, or “hardest” — or choose a pace below.",
        )
        width, height = surface.get_size()
        self._layout_buttons()
        card_width = min(350, (width - 150) // 3)
        gap = 28
        total_width = card_width * 3 + gap * 2
        left = (width - total_width) // 2
        card_y = max(215, height // 2 - 65)
        for index, (level, description, accent, button) in enumerate(
            zip(self.LEVELS, self.DESCRIPTIONS, self.ACCENTS, self._buttons)
        ):
            x = left + index * (card_width + gap)
            Card(
                pygame.Rect(x, card_y, card_width, 195),
                title=level,
                body=[description, f"{5 + index * 2}–{7 + index * 2} minute adventure"],
                accent=accent,
            ).draw(surface)
            button.rect = pygame.Rect(x + 24, card_y + 126, card_width - 48, 48)
            button.draw(surface)
        self._back_button.rect.topleft = (52, height - 112)
        self._back_button.draw(surface)
        draw_text(
            surface,
            "Difficulty changes the notes, the questions, and the maze route.",
            (width // 2, card_y + 240),
            size=15,
            color=COLORS["text_muted"],
            align="center",
        )

    def _layout_buttons(self) -> None:
        """Create one clickable choice for each difficulty level."""
        width, height = self.game.screen.get_size()
        card_width = min(350, (width - 150) // 3)
        gap = 28
        left = (width - (card_width * 3 + gap * 2)) // 2
        card_y = max(215, height // 2 - 65)
        if not self._buttons:
            self._buttons = [
                Button(
                    pygame.Rect(0, 0, 250, 48),
                    f"CHOOSE {level.upper()}",
                    accent,
                )
                for level, accent in zip(self.LEVELS, self.ACCENTS)
            ]
        for index in range(len(self.LEVELS)):
            x = left + index * (card_width + gap)
            self._buttons[index].rect = pygame.Rect(
                x + 24,
                card_y + 126,
                card_width - 48,
                48,
            )

    def _select_level(self, level: str) -> None:
        """Save the course selection and open the five learning-note pages."""
        domain = self.game.state.domain
        if domain is None:
            from scenes.domain_scene import DomainScene

            self.toast.show("Choose a learning domain first.", COLORS["yellow"])
            self.game.scenes.change(DomainScene(self.game))
            return
        self.game.state.select_course(domain, level)
        self.game.scenes.change(NotesScene(self.game))
