"""Verify lesson examples run and match their displayed expected output."""

import contextlib
import io
import unittest

from utils.content import load_course


class CourseExampleTests(unittest.TestCase):
    """Check each course content set and executable Python examples."""

    def test_all_nine_courses_have_five_complete_topic_quizzes(self) -> None:
        """Each domain and difficulty contains five topics and fifteen valid MCQs."""
        for domain in ("Python", "SQL", "Logical Reasoning"):
            for level in ("Beginner", "Intermediate", "Advanced"):
                with self.subTest(domain=domain, level=level):
                    topics = load_course(domain, level)
                    self.assertEqual(len(topics), 5)
                    self.assertEqual(sum(len(topic["mcqs"]) for topic in topics), 15)
                    for topic in topics:
                        self.assertTrue(topic["example"].strip())
                        self.assertTrue(topic["example_output"].strip())
                        self.assertTrue(all(note.strip() for note in topic["notes"]))

    def test_python_examples_match_their_displayed_output(self) -> None:
        """Every Python notes example is runnable and displays its expected result."""
        for level in ("Beginner", "Intermediate", "Advanced"):
            topics = load_course("Python", level)
            for topic in topics:
                with self.subTest(level=level, topic=topic["title"]):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        exec(topic["example"], {"__name__": "__main__"})
                    self.assertEqual(
                        output.getvalue().strip(),
                        topic["example_output"].strip(),
                    )


if __name__ == "__main__":
    unittest.main()
