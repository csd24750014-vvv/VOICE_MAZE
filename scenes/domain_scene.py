"""Subject selection screen for Python, SQL, and logic learning paths."""

from typing import TYPE_CHECKING

import pygame

from scenes.base_scene import BaseScene
from scenes.level_scene import LevelScene
from ui.components import Button, Card
from ui.theme import COLORS, draw_text
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class DomainScene(BaseScene):
    """Let the learner choose the subject for the next maze run."""

    DOMAINS = ("Python", "SQL", "Logical Reasoning")
    DESCRIPTIONS = (
        "Build practical programming fluency",
        "Query, analyze, and shape data",
        "Practice patterns and problem solving",
    )
    ACCENTS = (COLORS["cyan"], COLORS["purple"], COLORS["pink"])

    def __init__(self, game: "Game") -> None:
        """Create the three domain cards and a menu-navigation button."""
        super().__init__(game)
        self._buttons: list[Button] = []
        self._back_button = Button(pygame.Rect(0, 0, 150, 44), "BACK", COLORS["text_muted"])

    def handle_command(self, command: VoiceCommand) -> None:
        """Open the selected domain or return to the main menu."""
        if command.action == "select_domain" and command.value in self.DOMAINS:
            self._select_domain(command.value)
        elif command.action == "back":
            from scenes.menu_scene import MenuScene

            self.game.scenes.change(MenuScene(self.game))

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle mouse selection of a subject or the back control."""
        self._layout_buttons()
        if self._back_button.handle_event(event):
            from scenes.menu_scene import MenuScene

            self.game.scenes.change(MenuScene(self.game))
            return
        for button, domain in zip(self._buttons, self.DOMAINS):
            if button.handle_event(event):
                self._select_domain(domain)
                return

    def draw(self, surface: pygame.Surface) -> None:
        """Display subject cards with simple summaries and spoken choices."""
        self.draw_shell(
            surface,
            "Step 1 of 3",
            "Choose your learning domain",
            "Say a subject naturally — e.g. “go with Python”, “let’s do SQL”, or “choose logic”.",
        )
        width, height = surface.get_size()
        self._layout_buttons()
        card_width = min(350, (width - 150) // 3)
        gap = 28
        total_width = card_width * 3 + gap * 2
        left = (width - total_width) // 2
        card_y = max(215, height // 2 - 65)
        for index, (domain, description, accent, button) in enumerate(
            zip(self.DOMAINS, self.DESCRIPTIONS, self.ACCENTS, self._buttons)
        ):
            x = left + index * (card_width + gap)
            card = Card(
                pygame.Rect(x, card_y, card_width, 195),
                title=domain,
                body=[description, "5 topics  •  5 knowledge gates"],
                accent=accent,
            )
            card.draw(surface)
            button.rect = pygame.Rect(x + 24, card_y + 126, card_width - 48, 48)
            button.draw(surface)
        self._back_button.rect.topleft = (52, height - 112)
        self._back_button.draw(surface)
        draw_text(
            surface,
            "Your chosen subject stays selected while you explore all three levels.",
            (width // 2, card_y + 240),
            size=15,
            color=COLORS["text_muted"],
            align="center",
        )

    def _layout_buttons(self) -> None:
        """Create one clickable card action for each available subject."""
        width, height = self.game.screen.get_size()
        card_width = min(350, (width - 150) // 3)
        gap = 28
        left = (width - (card_width * 3 + gap * 2)) // 2
        card_y = max(215, height // 2 - 65)
        if not self._buttons:
            self._buttons = [
                Button(
                    pygame.Rect(0, 0, 250, 48),
                    f"EXPLORE {domain.upper()}",
                    accent,
                )
                for domain, accent in zip(self.DOMAINS, self.ACCENTS)
            ]
        for index in range(len(self.DOMAINS)):
            x = left + index * (card_width + gap)
            self._buttons[index].rect = pygame.Rect(
                x + 24,
                card_y + 126,
                card_width - 48,
                48,
            )

    def _select_domain(self, domain: str) -> None:
        """Save the domain and continue to difficulty selection."""
        self.game.state.domain = domain
        self.game.scenes.change(LevelScene(self.game))
