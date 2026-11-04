"""Test score, time-bonus, and answer-accuracy formulas."""

import unittest

from utils.scoring import (
    calculate_accuracy,
    calculate_completion_bonus,
    calculate_score,
    door_points,
    question_points,
)


class ScoringTests(unittest.TestCase):
    """Keep the difficulty weights and boundary behavior deterministic."""

    def test_difficulty_weights_increase_with_level(self) -> None:
        """Higher difficulties award more points per answer and topic door."""
        self.assertEqual(
            [question_points(level) for level in ("Beginner", "Intermediate", "Advanced")],
            [100, 150, 200],
        )
        self.assertEqual(
            [door_points(level) for level in ("Beginner", "Intermediate", "Advanced")],
            [50, 75, 100],
        )

    def test_accuracy_handles_empty_and_partial_results(self) -> None:
        """Accuracy is a percentage and an unanswered run starts at zero."""
        self.assertEqual(calculate_accuracy(0, 0), 0.0)
        self.assertEqual(calculate_accuracy(3, 4), 75.0)

    def test_completion_bonus_is_bounded_and_only_for_success(self) -> None:
        """Successful runs get a decreasing nonnegative time bonus."""
        self.assertEqual(calculate_completion_bonus(0, True), 600)
        self.assertEqual(calculate_completion_bonus(120, True), 360)
        self.assertEqual(calculate_completion_bonus(400, True), 0)
        self.assertEqual(calculate_completion_bonus(10, False), 0)

    def test_score_combines_correct_answers_gates_and_time(self) -> None:
        """The completed beginner score matches all three documented factors."""
        self.assertEqual(
            calculate_score(5, 2, True, 120, "Beginner"),
            960,
        )
        self.assertEqual(
            calculate_score(5, 2, False, 120, "Beginner"),
            600,
        )

    def test_invalid_inputs_are_rejected(self) -> None:
        """Invalid counts and unknown levels do not produce success-shaped values."""
        with self.assertRaises(ValueError):
            calculate_accuracy(2, 1)
        with self.assertRaises(ValueError):
            question_points("expert")
        with self.assertRaises(ValueError):
            calculate_score(1, 6, False, 0, "Beginner")


if __name__ == "__main__":
    unittest.main()
