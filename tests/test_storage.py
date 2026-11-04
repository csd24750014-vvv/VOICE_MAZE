"""Test persistent run history and personal best-time handling."""

import tempfile
import unittest
from pathlib import Path

from utils.storage import load_scores, record_result


class ScoreStorageTests(unittest.TestCase):
    """Verify score writes are readable and only completed runs set best times."""

    def test_results_persist_and_completed_runs_update_best_time(self) -> None:
        """A later faster completion becomes the course best and runs remain saved."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            score_path = Path(temporary_directory) / "scores.json"
            first = record_result(
                "Python", "Beginner", 100, 80.0, 90.0, True, path=score_path
            )
            unfinished = record_result(
                "Python", "Beginner", 50, 40.0, 30.0, False, path=score_path
            )
            faster = record_result(
                "Python", "Beginner", 150, 90.0, 60.0, True, path=score_path
            )

            stored = load_scores(score_path)
            course = stored["courses"]["python_beginner"]
            self.assertTrue(first["is_best_time"])
            self.assertFalse(unfinished["is_best_time"])
            self.assertTrue(faster["is_best_time"])
            self.assertEqual(course["best_time_seconds"], 60.0)
            self.assertEqual(len(course["runs"]), 3)
            self.assertEqual(course["best_score"], 150)

    def test_missing_score_file_is_treated_as_an_empty_store(self) -> None:
        """A fresh install can start without a pre-created score history."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            self.assertEqual(
                load_scores(Path(temporary_directory) / "not-created.json"),
                {"version": 1, "courses": {}},
            )


if __name__ == "__main__":
    unittest.main()
