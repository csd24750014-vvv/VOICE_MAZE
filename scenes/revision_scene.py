"""Focused revision page shown after an incorrect answer at a maze door."""

from typing import TYPE_CHECKING, Callable

import pygame

from scenes.base_scene import BaseScene
from ui.components import Button, Card
from ui.theme import COLORS, draw_rounded_rect, draw_text
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class RevisionScene(BaseScene):
    """Show the specific missed topic and explanation before retry or results."""

    def __init__(
        self,
        game: "Game",
        topic: dict,
        wrong_question: str,
        explanation: str,
        retry_available: bool,
        on_retry: Callable[[], None],
        on_results: Callable[[], None],
        on_cancel: Callable[[], None],
    ) -> None:
        """Store the topic, missed answer, and callbacks for the next action."""
        super().__init__(game)
        self.topic = topic
        self.wrong_question = wrong_question
        self.explanation = explanation
        self.retry_available = retry_available
        self.on_retry = on_retry
        self.on_results = on_results
        self.on_cancel = on_cancel
        self._primary = Button(
            pygame.Rect(0, 0, 230, 50),
            "RETRY DOOR" if retry_available else "VIEW RESULTS",
            COLORS["cyan"] if retry_available else COLORS["purple"],
        )
        self._return = Button(pygame.Rect(0, 0, 190, 50), "RETURN TO MAZE", COLORS["text_muted"])

    def handle_command(self, command: VoiceCommand) -> None:
        """Retry the quiz, view the final result, or return to its locked door."""
        if command.action == "retry" and self.retry_available:
            self._retry()
        elif command.action == "results" and not self.retry_available:
            self.on_results()
        elif command.action in {"back", "return_to_maze"}:
            if self.retry_available:
                self.on_cancel()
            else:
                self.on_results()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle the retry, results, and maze-return mouse controls."""
        self._layout_buttons()
        if self._primary.handle_event(event):
            if self.retry_available:
                self._retry()
            else:
                self.on_results()
            return
        if self.retry_available and self._return.handle_event(event):
            self.on_cancel()

    def draw(self, surface: pygame.Surface) -> None:
        """Present the wrong answer explanation, notes, and matching example."""
        width, height = surface.get_size()
        self.draw_shell(
            surface,
            "Revise  •  Learn this door’s topic",
            str(self.topic["title"]),
            "A missed answer is a cue to review. Take a moment, then try again.",
        )
        card_rect = pygame.Rect(64, 164, width - 128, height - 315)
        Card(
            card_rect,
            title="Review your answer",
            body=[
                f"Question: {self.wrong_question}",
                f"Why this answer works: {self.explanation}",
            ],
            accent=COLORS["red"],
        ).draw(surface)
        note_y = card_rect.y + 105
        draw_text(
            surface,
            "KEY NOTES",
            (card_rect.x + 30, note_y),
            size=13,
            color=COLORS["cyan"],
            role="heading",
        )
        for index, note in enumerate(self.topic["notes"]):
            draw_text(
                surface,
                f"•  {note}",
                (card_rect.x + 34, note_y + 29 + index * 29),
                size=16,
                color=COLORS["text"],
            )
        self._draw_example(
            surface,
            pygame.Rect(
                card_rect.x + 30,
                card_rect.bottom - 116,
                card_rect.width - 60,
                94,
            ),
        )
        self._layout_buttons()
        self._primary.draw(surface)
        if self.retry_available:
            self._return.draw(surface)
        if not self.retry_available:
            draw_text(
                surface,
                "Both attempts are used. Review your result and restart when ready.",
                (width // 2, height - 68),
                size=14,
                color=COLORS["text_muted"],
                align="center",
            )

    def _draw_example(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the topic's code/example snippet in a contrasting block."""
        draw_rounded_rect(
            surface,
            rect,
            (12, 17, 32),
            radius=12,
            border_color=COLORS["border"],
        )
        draw_text(
            surface,
            "EXAMPLE",
            (rect.x + 16, rect.y + 12),
            size=11,
            color=COLORS["purple"],
            role="heading",
        )
        lines = str(self.topic["example"]).splitlines()[:2]
        for index, line in enumerate(lines):
            draw_text(
                surface,
                line[:120],
                (rect.x + 18, rect.y + 35 + index * 22),
                size=14,
                color=COLORS["green"] if "=" in line else COLORS["text"],
                role="mono",
            )

    def _layout_buttons(self) -> None:
        """Place primary and return actions at the bottom of the window."""
        width, height = self.game.screen.get_size()
        self._primary.rect = pygame.Rect(width // 2 - 245, height - 120, 230, 50)
        self._return.rect = pygame.Rect(width // 2 + 15, height - 120, 210, 50)

    def _retry(self) -> None:
        """Reset the parent quiz before returning to the locked door."""
        self.on_retry()
        self.game.scenes.pop()
