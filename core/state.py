"""Mutable application state shared by game scenes."""

from dataclasses import dataclass
from typing import Optional

from utils.scoring import calculate_accuracy


@dataclass
class GameState:
    """Track the selected course and progress for one game session."""

    domain: Optional[str] = None
    level: Optional[str] = None
    attempt_limit: int = 2
    attempts_remaining: int = 2
    score: int = 0
    questions_answered: int = 0
    questions_correct: int = 0
    doors_unlocked: int = 0
    completion_time: Optional[float] = None
    elapsed_seconds: float = 0.0
    run_started_at: Optional[float] = None
    completed: bool = False

    def select_course(self, domain: str, level: str) -> None:
        """Set the selected course and start a fresh run for it."""
        self.domain = domain
        self.level = level
        self.reset_level()

    def reset_level(self) -> None:
        """Restore all per-run counters while preserving the selected course."""
        self.attempts_remaining = self.attempt_limit
        self.score = 0
        self.questions_answered = 0
        self.questions_correct = 0
        self.doors_unlocked = 0
        self.completion_time = None
        self.elapsed_seconds = 0.0
        self.run_started_at = None
        self.completed = False

    def record_answer(self, is_correct: bool, points: int = 0) -> None:
        """Record one assessed answer and award points only for correct answers."""
        self.questions_answered += 1
        if is_correct:
            self.questions_correct += 1
            self.score += max(0, points)

    def use_attempt(self) -> bool:
        """Consume one attempt and report whether any attempts remain."""
        if self.attempts_remaining <= 0:
            return False
        self.attempts_remaining -= 1
        return self.attempts_remaining > 0

    @property
    def attempts_used(self) -> int:
        """Return the number of attempts consumed in the current run."""
        return self.attempt_limit - self.attempts_remaining

    @property
    def accuracy(self) -> float:
        """Return answer accuracy as a percentage, or zero before answers exist."""
        return calculate_accuracy(self.questions_correct, self.questions_answered)
