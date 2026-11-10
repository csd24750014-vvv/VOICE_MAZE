"""Difficulty selection screen for the selected learning domain."""

from typing import TYPE_CHECKING

import pygame

from scenes.base_scene import BaseScene
from scenes.notes_scene import NotesScene
from ui.components import Button
from ui.theme import COLORS, draw_rounded_rect, draw_text, font
from utils.storage import ScoreStorageError, unlocked_levels
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class LevelScene(BaseScene):
    """Let the learner select beginner, intermediate, or advanced content."""

    LEVELS = ("Beginner", "Intermediate", "Advanced")
    DESCRIPTIONS = (
        "Learn the maze with a short, guided route.",
        "Navigate extra turns and misleading dead ends.",
        "Plan a route through the largest, most complex maze.",
    )
    ACCENTS = (COLORS["green"], COLORS["cyan"], COLORS["purple"])

    def __init__(self, game: "Game") -> None:
        """Create difficulty controls for the currently selected subject."""
        super().__init__(game)
        self._buttons: list[Button] = []
        self._back_button = Button(pygame.Rect(0, 0, 150, 44), "BACK", COLORS["text_muted"])
        self._unlocked_levels = frozenset({"Beginner"})
        self._progress_error = ""
        if game.state.domain is not None:
            try:
                self._unlocked_levels = unlocked_levels(game.state.domain)
            except ScoreStorageError as error:
                self._progress_error = str(error)
                self.toast.show(
                    "Saved progress could not be read; only Beginner is available.",
                    COLORS["red"],
                )

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
        card_y = max(190, height // 2 - 180)
        for index, (level, description, accent, button) in enumerate(
            zip(self.LEVELS, self.DESCRIPTIONS, self.ACCENTS, self._buttons)
        ):
            x = left + index * (card_width + gap)
            is_unlocked = level in self._unlocked_levels
            self._draw_level_card(
                surface,
                pygame.Rect(x, card_y, card_width, 300),
                index,
                description,
                accent,
                is_unlocked,
            )
            button.rect = pygame.Rect(x + 24, card_y + 226, card_width - 48, 50)
            button.enabled = is_unlocked
            button.label = "START LEVEL" if is_unlocked else "LOCKED"
            button.draw(surface)
        self._back_button.rect.topleft = (52, height - 112)
        self._back_button.draw(surface)

    def _layout_buttons(self) -> None:
        """Create one clickable choice for each difficulty level."""
        width, height = self.game.screen.get_size()
        card_width = min(350, (width - 150) // 3)
        gap = 28
        left = (width - (card_width * 3 + gap * 2)) // 2
        card_y = max(190, height // 2 - 180)
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
                card_y + 226,
                card_width - 48,
                50,
            )
            level = self.LEVELS[index]
            is_unlocked = level in self._unlocked_levels
            self._buttons[index].enabled = is_unlocked
            self._buttons[index].label = (
                "START LEVEL" if is_unlocked else "LOCKED"
            )

    def _draw_level_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        index: int,
        description: str,
        accent: tuple[int, int, int],
        unlocked: bool,
    ) -> None:
        """Draw a clean difficulty card with separately spaced title and status."""
        active_accent = accent if unlocked else COLORS["text_muted"]
        pygame.draw.rect(surface, COLORS["black"], rect.move(0, 7), border_radius=20)
        draw_rounded_rect(
            surface,
            rect,
            COLORS["surface"],
            radius=20,
            border_color=active_accent,
            border_width=2 if unlocked else 1,
        )
        pygame.draw.rect(
            surface,
            active_accent,
            pygame.Rect(rect.x + 1, rect.y + 20, 4, rect.height - 40),
            border_radius=3,
        )
        draw_text(
            surface,
            self.LEVELS[index].upper(),
            (rect.x + 24, rect.y + 25),
            size=23,
            color=active_accent,
            role="heading",
        )
        status = "AVAILABLE" if unlocked else "LOCKED"
        status_rect = pygame.Rect(rect.right - 112, rect.y + 24, 88, 27)
        draw_rounded_rect(
            surface,
            status_rect,
            (17, 24, 39),
            radius=10,
            border_color=active_accent,
        )
        draw_text(
            surface,
            status,
            status_rect.center,
            size=10,
            color=active_accent,
            role="heading",
            align="center",
        )

        description_color = COLORS["text"] if unlocked else COLORS["text_muted"]
        description_font = font(16)
        wrapped_description = _wrap_description(
            description,
            description_font,
            rect.width - 52,
        )
        for line_index, line in enumerate(wrapped_description[:3]):
            draw_text(
                surface,
                line,
                (rect.x + 24, rect.y + 82 + line_index * 23),
                size=16,
                color=description_color,
            )
        maze_cells = (9, 11, 13)[index]
        draw_text(
            surface,
            f"{maze_cells} × {maze_cells} maze  •  5 topic doors",
            (rect.x + 24, rect.y + 158),
            size=13,
            color=active_accent,
            role="heading",
        )
        progress_message = (
            "Ready to play"
            if unlocked
            else (
                "Complete Beginner to unlock"
                if index == 1
                else "Complete Intermediate to unlock"
            )
        )
        draw_text(
            surface,
            progress_message,
            (rect.x + 24, rect.y + 188),
            size=13,
            color=COLORS["green"] if unlocked else COLORS["yellow"],
        )

    def _select_level(self, level: str) -> None:
        """Check progression before saving a course and opening its lesson pages."""
        domain = self.game.state.domain
        if domain is None:
            from scenes.domain_scene import DomainScene

            self.toast.show("Choose a learning domain first.", COLORS["yellow"])
            self.game.scenes.change(DomainScene(self.game))
            return
        if level not in self._unlocked_levels:
            prerequisite = {
                "Intermediate": "Complete Beginner first to unlock Intermediate.",
                "Advanced": "Complete Intermediate first to unlock Advanced.",
            }.get(level, "That difficulty is locked.")
            if self._progress_error:
                self.toast.show(
                    f"{prerequisite} Saved progress could not be loaded.",
                    COLORS["red"],
                )
            else:
                self.toast.show(prerequisite, COLORS["yellow"])
            return
        self.game.state.select_course(domain, level)
        self.game.scenes.change(NotesScene(self.game))


def _wrap_description(
    text: str,
    text_font: pygame.font.Font,
    max_width: int,
) -> list[str]:
    """Wrap one card description to fit without running beneath its button."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and text_font.size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
