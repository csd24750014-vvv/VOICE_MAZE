"""Deterministic score and answer-accuracy formulas for course runs."""

from typing import Final

_QUESTION_POINTS: Final[dict[str, int]] = {
    "beginner": 100,
    "intermediate": 150,
    "advanced": 200,
}
_DOOR_POINTS: Final[dict[str, int]] = {
    "beginner": 50,
    "intermediate": 75,
    "advanced": 100,
}


def question_points(level: str) -> int:
    """Return the points awarded for each correct answer at this difficulty."""
    normalized = level.strip().casefold()
    if normalized not in _QUESTION_POINTS:
        raise ValueError(f"Unknown difficulty level: {level!r}.")
    return _QUESTION_POINTS[normalized]


def door_points(level: str) -> int:
    """Return the bonus for passing one topic gate at this difficulty."""
    normalized = level.strip().casefold()
    if normalized not in _DOOR_POINTS:
        raise ValueError(f"Unknown difficulty level: {level!r}.")
    return _DOOR_POINTS[normalized]


def calculate_accuracy(correct_answers: int, total_answers: int) -> float:
    """Return the percentage of correct answers, or zero when none were answered."""
    if total_answers < 0 or correct_answers < 0 or correct_answers > total_answers:
        raise ValueError("Answer counts must satisfy 0 <= correct <= total.")
    if total_answers == 0:
        return 0.0
    return correct_answers / total_answers * 100.0


def calculate_completion_bonus(elapsed_seconds: float, completed: bool) -> int:
    """Award a bounded speed bonus only to a successfully completed run."""
    if elapsed_seconds < 0:
        raise ValueError("Elapsed time cannot be negative.")
    if not completed:
        return 0
    return max(0, 600 - int(elapsed_seconds) * 2)


def calculate_score(
    correct_answers: int,
    doors_unlocked: int,
    completed: bool,
    elapsed_seconds: float,
    level: str,
) -> int:
    """Combine correct answers, unlocked gates, and a completion-time bonus."""
    if correct_answers < 0 or not 0 <= doors_unlocked <= 5:
        raise ValueError("Correct-answer and unlocked-door counts cannot be negative.")
    normalized = level.strip().casefold()
    if normalized not in _QUESTION_POINTS:
        raise ValueError(f"Unknown difficulty level: {level!r}.")
    base = correct_answers * _QUESTION_POINTS[normalized]
    gate_bonus = doors_unlocked * _DOOR_POINTS[normalized]
    time_bonus = calculate_completion_bonus(elapsed_seconds, completed)
    return base + gate_bonus + time_bonus
