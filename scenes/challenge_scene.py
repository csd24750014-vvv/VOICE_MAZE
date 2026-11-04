"""Three-question voice or mouse quiz shown at each locked maze door."""

import time
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Callable, Optional

import pygame

from scenes.base_scene import BaseScene
from ui.components import Button, Card, ProgressBar
from ui.theme import COLORS, draw_text
from utils.content import (
    ContentLoadError,
    correct_option_index,
    load_course,
    normalize_answer,
    question_options,
)
from utils.scoring import door_points, question_points
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class ChallengeScene(BaseScene):
    """Assess one topic with three questions before opening its locked door."""

    def __init__(
        self,
        game: "Game",
        door_id: int,
        on_unlocked: Callable[[int], None],
        on_cancelled: Callable[[int], None],
    ) -> None:
        """Load the selected door's topic and prepare answer controls."""
        super().__init__(game)
        if not 1 <= door_id <= 5:
            raise ValueError(f"Door number must be between 1 and 5, got {door_id}.")
        domain = game.state.domain
        level = game.state.level
        if domain is None or level is None:
            raise ValueError("Select a domain and difficulty before answering a door quiz.")
        self.door_id = door_id
        self.on_unlocked = on_unlocked
        self.on_cancelled = on_cancelled
        self.topic: Optional[dict] = None
        self.questions: list[dict] = []
        self.load_error = ""
        self.question_index = 0
        self._feedback = ""
        self._feedback_remaining = 0.0
        self._success_pending = False
        self._revision_open = False
        self._option_buttons: list[Button] = []
        self._return_button = Button(pygame.Rect(0, 0, 220, 48), "RETURN TO MAZE", COLORS["text_muted"])
        self._load_topic(domain, level)

    def command_context(self) -> Optional[str]:
        """Interpret unrecognized phrases as spoken answer text on this screen."""
        return "answer"

    def handle_command(self, command: VoiceCommand) -> None:
        """Accept letter, answer-text, or navigation voice commands."""
        if command.action == "option" and command.value:
            self.submit_answer(command.value)
        elif command.action == "answer_text" and command.value:
            self.submit_answer_text(command.value)
        elif command.action == "back" or command.action == "return_to_maze":
            self._cancel()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Submit a clicked answer or close a quiz with unavailable content."""
        self._layout_controls()
        if self.load_error:
            if self._return_button.handle_event(event):
                self._cancel()
            return
        if self._feedback or self._revision_open:
            return
        for index, button in enumerate(self._option_buttons):
            if button.handle_event(event):
                self.submit_answer(chr(ord("A") + index))
                return

    def update(self, delta_seconds: float) -> None:
        """Advance question feedback without pausing the main game loop."""
        super().update(delta_seconds)
        if self._feedback:
            self._feedback_remaining = max(0.0, self._feedback_remaining - delta_seconds)
        if self._feedback and self._feedback_remaining == 0:
            self._feedback = ""
            if self._success_pending:
                self._complete_challenge()
            else:
                self.question_index += 1

    def draw(self, surface: pygame.Surface) -> None:
        """Render the question card, four answers, and quiz progress."""
        topic_title = self.topic["title"] if self.topic is not None else "Topic unavailable"
        self.draw_shell(
            surface,
            f"Assess  •  Door {self.door_id} of 5",
            f"Knowledge gate: {topic_title}",
            "Say the option letter or answer naturally — e.g. “I choose B” or read the answer.",
        )
        width, height = surface.get_size()
        if self.load_error:
            Card(
                pygame.Rect(100, 195, width - 200, 320),
                title="This topic quiz is unavailable",
                body=[
                    self.load_error,
                    "The door remains locked. Check the course content and try again.",
                ],
                accent=COLORS["red"],
            ).draw(surface)
            self._layout_controls()
            self._return_button.draw(surface)
            return
        if self.topic is None or not self.questions:
            return

        question = self.questions[self.question_index]
        draw_text(
            surface,
            f"QUESTION  {self.question_index + 1} / 3     •     ATTEMPT  "
            f"{min(self.game.state.attempt_limit, self.game.state.attempts_used + 1)}"
            f" / {self.game.state.attempt_limit}",
            (100, 161),
            size=14,
            color=COLORS["cyan"],
            role="heading",
        )
        Card(
            pygame.Rect(88, 186, width - 176, 132),
            title="QUESTION",
            body=[str(question["question"])],
            accent=COLORS["purple"],
        ).draw(surface, padding=22)
        self._layout_controls()
        for button in self._option_buttons:
            button.draw(surface)
        progress = ProgressBar(
            pygame.Rect(100, height - 90, width - 200, 8),
            self.question_index,
            3,
            COLORS["purple"],
        )
        progress.draw(surface)
        if self._feedback:
            color = COLORS["green"] if self._success_pending else COLORS["red"]
            draw_text(
                surface,
                self._feedback,
                (width // 2, height - 111),
                size=17,
                color=color,
                role="heading",
                align="center",
            )

    def submit_answer(self, answer: str) -> bool:
        """Record one A–D response and open revision immediately when it is wrong."""
        if self.load_error or self.topic is None or self._feedback or self._revision_open:
            return False
        normalized = answer.strip().upper()
        if normalized not in {"A", "B", "C", "D"}:
            return self.submit_answer_text(answer)
        self._record_selection(ord(normalized) - ord("A"))
        return True

    def submit_answer_text(self, answer: str) -> bool:
        """Match spoken answer text to one of this question's four choices."""
        if self.load_error or self.topic is None or self._feedback or self._revision_open:
            return False
        question = self.questions[self.question_index]
        options = question_options(question)
        normalized = normalize_answer(answer)
        if not normalized:
            self.toast.show("Say the option letter or read an answer aloud.", COLORS["yellow"])
            return False

        exact_matches = [
            index
            for index, option in enumerate(options)
            if normalized == normalize_answer(option)
        ]
        if len(exact_matches) == 1:
            self._record_selection(exact_matches[0])
            return True

        scored_matches = [
            (SequenceMatcher(None, normalized, normalize_answer(option)).ratio(), index)
            for index, option in enumerate(options)
        ]
        scored_matches.sort(reverse=True)
        if (
            scored_matches
            and scored_matches[0][0] >= 0.84
            and (len(scored_matches) == 1 or scored_matches[0][0] - scored_matches[1][0] >= 0.08)
        ):
            self._record_selection(scored_matches[0][1])
            return True
        self.toast.show("That answer didn’t match an option. Try its full wording.", COLORS["yellow"])
        return False

    def _load_topic(self, domain: str, level: str) -> None:
        """Load the exact numbered door topic and its three multiple-choice items."""
        try:
            topics = load_course(domain, level)
        except ContentLoadError as error:
            self.load_error = str(error)
            return
        self.topic = topics[self.door_id - 1]
        self.questions = self.topic["mcqs"]

    def _layout_controls(self) -> None:
        """Keep quiz options readable and centered at the current window size."""
        width, height = self.game.screen.get_size()
        self._return_button.rect = pygame.Rect(
            width // 2 - 110,
            min(height - 186, 542),
            220,
            48,
        )
        if self.load_error:
            return
        if not self._option_buttons:
            self._option_buttons = [
                Button(pygame.Rect(0, 0, 1000, 68), f"{letter}. Answer", COLORS["cyan"])
                for letter in "ABCD"
            ]
        if not self.questions:
            return
        options = question_options(self.questions[self.question_index])
        top = 336
        bottom = height - 139
        available_height = max(220, bottom - top)
        gap = 10
        button_height = min(74, (available_height - 3 * gap) // 4)
        for index, button in enumerate(self._option_buttons):
            button.rect = pygame.Rect(
                100,
                top + index * (button_height + gap),
                width - 200,
                button_height,
            )
            button.label = f"{chr(ord('A') + index)}.  {options[index]}"

    def _record_selection(self, selected_index: int) -> None:
        """Track an answer, then continue or show topic revision for a mistake."""
        question = self.questions[self.question_index]
        is_correct = selected_index == correct_option_index(question)
        self.game.state.record_answer(
            is_correct,
            points=(
                question_points(self.game.state.level or "")
                if is_correct
                else 0
            ),
        )
        if is_correct:
            self._success_pending = self.question_index == 2
            self._feedback = "Correct — nice work!" if not self._success_pending else "All three answers correct!"
            self._feedback_remaining = 0.65
            return
        self._open_revision(question)

    def _open_revision(self, question: dict) -> None:
        """Consume one level attempt and show notes for this exact topic."""
        if self.topic is None:
            return
        self.game.state.use_attempt()
        self.game.state.completed = False
        run_started_at = self.game.state.run_started_at
        if run_started_at is not None:
            self.game.state.elapsed_seconds = max(
                self.game.state.elapsed_seconds,
                time.monotonic() - run_started_at,
            )
        self.game.state.completion_time = self.game.state.elapsed_seconds
        self._revision_open = True
        from scenes.revision_scene import RevisionScene

        self.game.scenes.push(
            RevisionScene(
                self.game,
                self.topic,
                wrong_question=str(question["question"]),
                explanation=str(question["explanation"]),
                retry_available=self.game.state.attempts_remaining > 0,
                on_retry=self._retry,
                on_results=self._show_failed_results,
                on_cancel=self._cancel,
            )
        )

    def _retry(self) -> None:
        """Restart this door's full three-question set after revision."""
        self.question_index = 0
        self._feedback = ""
        self._success_pending = False
        self._revision_open = False

    def _complete_challenge(self) -> None:
        """Award a door bonus and notify the maze that its barrier can open."""
        if self.topic is None:
            return
        self.game.state.doors_unlocked += 1
        self.game.state.score += door_points(self.game.state.level or "")
        self.on_unlocked(self.door_id)
        self.game.scenes.pop()

    def _show_failed_results(self) -> None:
        """End the level after its second failed attempt and show the result card."""
        self.game.state.completed = False
        self.game.state.completion_time = self.game.state.elapsed_seconds
        from scenes.result_scene import ResultScene

        self.game.scenes.clear_and_change(ResultScene(self.game))

    def _cancel(self) -> None:
        """Close the quiz and return control to the still-locked maze door."""
        self.on_cancelled(self.door_id)
        if self.game.scenes.current is not self:
            self.game.scenes.pop()
        if self.game.scenes.current is self:
            self.game.scenes.pop()
