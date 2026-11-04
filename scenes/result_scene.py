"""Animated run summary with accuracy, persistence, and replay actions."""

import math
import time
from typing import TYPE_CHECKING, Any, Optional

import pygame

from scenes.base_scene import BaseScene
from ui.components import Button, Card, ProgressBar
from ui.theme import COLORS, draw_text, font
from utils.scoring import calculate_score
from utils.storage import ScoreStorageError, record_result
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class ResultScene(BaseScene):
    """Celebrate a finish or explain an incomplete run with its saved stats."""

    def __init__(self, game: "Game") -> None:
        """Calculate the final score and persist this course attempt once."""
        super().__init__(game)
        state = game.state
        if state.domain is None or state.level is None:
            raise ValueError("A selected domain and level are required for run results.")
        self.domain = state.domain
        self.level = state.level
        self.completed = state.completed
        self.elapsed_seconds = (
            state.completion_time
            if state.completion_time is not None
            else state.elapsed_seconds
        )
        self.score = calculate_score(
            state.questions_correct,
            state.doors_unlocked,
            self.completed,
            self.elapsed_seconds,
            self.level,
        )
        state.score = self.score
        self.accuracy = state.accuracy
        self.best_time: Optional[float] = None
        self.is_best_time = False
        self.storage_error = ""
        self._stored_record: Optional[dict[str, Any]] = None
        self._elapsed_animation = 0.0
        self._display_score = 0
        self._replay_button = Button(pygame.Rect(0, 0, 220, 52), "PLAY AGAIN", COLORS["cyan"])
        self._menu_button = Button(pygame.Rect(0, 0, 220, 52), "MAIN MENU", COLORS["purple"])
        self._save_result()

    def handle_command(self, command: VoiceCommand) -> None:
        """Replay the course or return to the main menu by voice."""
        if command.action == "play_again":
            self._play_again()
        elif command.action == "main_menu":
            self._main_menu()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle the two available results-screen actions."""
        self._layout_buttons()
        if self._replay_button.handle_event(event):
            self._play_again()
        elif self._menu_button.handle_event(event):
            self._main_menu()

    def update(self, delta_seconds: float) -> None:
        """Count score upward smoothly while processing microphone feedback."""
        super().update(delta_seconds)
        self._elapsed_animation += delta_seconds
        count_progress = min(1.0, self._elapsed_animation / 1.2)
        eased_progress = 1.0 - (1.0 - count_progress) ** 3
        self._display_score = int(self.score * eased_progress)

    def draw(self, surface: pygame.Surface) -> None:
        """Render status, animated score, stars, accuracy, and best-time badge."""
        width, height = surface.get_size()
        title = "MAZE COMPLETE" if self.completed else "RUN SUMMARY"
        subtitle = (
            f"{self.domain} / {self.level}  •  "
            f"{'All five topic gates cleared' if self.completed else 'Attempts used — every run teaches you something'}"
        )
        self.draw_shell(
            surface,
            "Results  •  Your learning run",
            title,
            subtitle,
        )

        self._draw_stars(surface, width // 2, 184)
        score_card = Card(
            pygame.Rect(width // 2 - 200, 220, 400, 128),
            title="TOTAL SCORE",
            body=[],
            accent=COLORS["cyan"] if self.completed else COLORS["purple"],
        )
        score_card.draw(surface)
        draw_text(
            surface,
            f"{self._display_score:,}",
            (width // 2, 288),
            size=38,
            color=COLORS["text"],
            role="heading",
            align="center",
        )

        card_y = 375
        card_width = min(340, (width - 160) // 3)
        gap = 24
        total_width = card_width * 3 + gap * 2
        left = (width - total_width) // 2
        values = (
            ("ACCURACY", f"{self.accuracy:.0f}%", COLORS["green"]),
            ("TIME TAKEN", _format_time(self.elapsed_seconds), COLORS["cyan"]),
            (
                "BEST TIME",
                _format_time(self.best_time) if self.best_time is not None else "—",
                COLORS["yellow"],
            ),
        )
        for index, (label, value, accent) in enumerate(values):
            x = left + index * (card_width + gap)
            Card(
                pygame.Rect(x, card_y, card_width, 112),
                title=label,
                body=[value],
                accent=accent,
            ).draw(surface)
        accuracy_width = max(120, total_width - 80)
        accuracy_x = (width - accuracy_width) // 2
        accuracy_bar = ProgressBar(
            pygame.Rect(accuracy_x, card_y + 132, accuracy_width, 12),
            self.accuracy,
            100,
            COLORS["green"],
        )
        accuracy_bar.draw(surface)

        if self.completed and self.is_best_time:
            draw_text(
                surface,
                "NEW PERSONAL BEST",
                (width // 2, card_y + 172),
                size=14,
                color=COLORS["yellow"],
                role="heading",
                align="center",
            )
        elif self.storage_error:
            draw_text(
                surface,
                "Score could not be saved: " + self.storage_error[:100],
                (width // 2, card_y + 172),
                size=13,
                color=COLORS["red"],
                align="center",
            )

        self._layout_buttons()
        self._replay_button.draw(surface)
        self._menu_button.draw(surface)
        draw_text(
            surface,
            "LEARN  →  PLAY  →  ASSESS  →  REVISE  →  UNLOCK",
            (width // 2, height - 79),
            size=14,
            color=COLORS["purple"],
            role="heading",
            align="center",
        )

    def _save_result(self) -> None:
        """Persist the run and remember whether it improved the course best time."""
        try:
            self._stored_record = record_result(
                domain=self.domain,
                level=self.level,
                score=self.score,
                accuracy=self.accuracy,
                elapsed_seconds=self.elapsed_seconds,
                completed=self.completed,
            )
        except ScoreStorageError as error:
            self.storage_error = str(error)
            return
        course = self._stored_record["course"]
        best_time = course["best_time_seconds"]
        self.best_time = float(best_time) if best_time is not None else None
        self.is_best_time = self._stored_record["is_best_time"]

    def _draw_stars(self, surface: pygame.Surface, center_x: int, center_y: int) -> None:
        """Show a small star rating based on course completion and accuracy."""
        if not self.completed:
            rating = 0
        elif self.accuracy >= 85:
            rating = 3
        elif self.accuracy >= 60:
            rating = 2
        else:
            rating = 1
        pulse = 0.85 + (math.sin(time.monotonic() * 2.5) + 1) * 0.075
        for index in range(3):
            color = COLORS["yellow"] if index < rating else COLORS["border"]
            star = font(34 if index == 1 else 28, "heading")
            rendered = star.render("★", True, color)
            bounds = rendered.get_rect(
                center=(center_x + (index - 1) * int(45 * pulse), center_y)
            )
            surface.blit(rendered, bounds)

    def _layout_buttons(self) -> None:
        """Keep replay and main-menu controls centered below the result cards."""
        width, height = self.game.screen.get_size()
        self._replay_button.rect = pygame.Rect(
            width // 2 - 232,
            height - 145,
            220,
            52,
        )
        self._menu_button.rect = pygame.Rect(
            width // 2 + 12,
            height - 145,
            220,
            52,
        )

    def _play_again(self) -> None:
        """Reset the run and return to the selected course's learning notes."""
        from scenes.notes_scene import NotesScene

        self.game.state.reset_level()
        self.game.scenes.clear_and_change(NotesScene(self.game))

    def _main_menu(self) -> None:
        """Discard the completed scene stack and open a fresh main menu."""
        from scenes.menu_scene import MenuScene

        self.game.scenes.clear_and_change(MenuScene(self.game))


def _format_time(seconds: Optional[float]) -> str:
    """Format elapsed seconds as minutes and seconds for result cards."""
    whole_seconds = max(0, int(seconds or 0))
    minutes, remaining_seconds = divmod(whole_seconds, 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"

