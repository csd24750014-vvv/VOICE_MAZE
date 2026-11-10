"""Tests for natural-language voice command recognition and cooldowns."""

import unittest

from voice.commands import CommandParser, parse_command


class NaturalCommandTests(unittest.TestCase):
    """Verify paraphrases map to stable actions without overmatching."""

    def test_start_phrases_map_to_menu_start(self) -> None:
        """Accept common ways of asking the game to begin."""
        for phrase in (
            "start",
            "start the game",
            "start the game please",
            "start learning",
            "can you start the game",
            "let's begin",
            "open the game",
        ):
            with self.subTest(phrase=phrase):
                command = parse_command(phrase)
                self.assertIsNotNone(command)
                self.assertEqual(command.action, "start")
        for phrase in ("ok go on", "go ahead", "let's go"):
            with self.subTest(phrase=phrase):
                self.assertEqual(parse_command(phrase).action, "start")

    def test_domain_and_level_paraphrases(self) -> None:
        """Recognize subject and difficulty choices inside natural sentences."""
        phrases = {
            "go with Python": ("select_domain", "Python"),
            "I want to learn SQL": ("select_domain", "SQL"),
            "let's do logical reasoning": ("select_domain", "Logical Reasoning"),
            "choose the easiest level": ("select_level", "Beginner"),
            "I would like medium difficulty": ("select_level", "Intermediate"),
            "give me the hardest challenge": ("select_level", "Advanced"),
        }
        for phrase, expected in phrases.items():
            with self.subTest(phrase=phrase):
                command = parse_command(phrase)
                self.assertIsNotNone(command)
                self.assertEqual((command.action, command.value), expected)

    def test_maze_directions_accept_natural_phrases(self) -> None:
        """Interpret polite movement requests as one directional command."""
        phrases = {
            "please move me up": "move_up",
            "turn to the left": "move_left",
            "head over to the right": "move_right",
            "walk down": "move_down",
            "move forward": "move_up",
            "go backward": "move_down",
        }
        for phrase, expected in phrases.items():
            with self.subTest(phrase=phrase):
                command = parse_command(phrase)
                self.assertIsNotNone(command)
                self.assertEqual(command.action, expected)

    def test_game_flow_paraphrases(self) -> None:
        """Recognize natural phrases for help, retry, replay, and navigation."""
        phrases = {
            "show me how to play": "how_to_play",
            "start the maze": "start_maze",
            "let me try again": "retry",
            "play the game again": "play_again",
            "go back to the main menu": "main_menu",
            "return to the maze": "return_to_maze",
            "show me the results": "results",
            "please quit the game": "quit",
            "move to the next page": "next",
            "go to the previous page": "back",
            "redo that quiz": "retry",
            "continue to the maze": "start_maze",
        }
        for phrase, expected in phrases.items():
            with self.subTest(phrase=phrase):
                command = parse_command(phrase)
                self.assertIsNotNone(command)
                self.assertEqual(command.action, expected)

    def test_notes_accept_flexible_start_and_continue_phrases(self) -> None:
        """Map flexible proceed phrases to the action available on each notes page."""
        for phrase in ("start", "start learning", "start the game", "begin the maze"):
            with self.subTest(phrase=phrase):
                command = parse_command(phrase, context="notes")
                self.assertEqual(command.action, "start_maze")

        for phrase in ("ok go on", "go ahead", "continue"):
            with self.subTest(phrase=phrase):
                command = parse_command(phrase, context="notes_final")
                self.assertEqual(command.action, "start_maze")

        self.assertEqual(
            parse_command("ok go on", context="notes").action,
            "next",
        )
        self.assertEqual(
            parse_command("next topic", context="notes_final").action,
            "next",
        )

    def test_negated_start_commands_do_not_start(self) -> None:
        """Never treat an explicit refusal as permission to start."""
        for phrase in (
            "don't start",
            "do not start",
            "please don't start the maze",
            "I do not want to start yet",
            "don't go on",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(parse_command(phrase).action, "cancel")
                self.assertEqual(
                    parse_command(phrase, context="notes_final").action,
                    "cancel",
                )

    def test_answers_preserve_text_and_accept_spoken_choices(self) -> None:
        """Keep quiz answer text intact and recognize letter-choice paraphrases."""
        self.assertEqual(
            parse_command("The correct response is Python", context="answer").action,
            "answer_text",
        )
        self.assertEqual(
            parse_command("Python", context="answer").action,
            "answer_text",
        )
        self.assertEqual(
            parse_command("I choose option B", context="answer").value,
            "B",
        )
        self.assertEqual(
            parse_command("The answer is D", context="answer").value,
            "D",
        )
        self.assertEqual(
            parse_command("I choose the third one", context="answer").value,
            "C",
        )

    def test_typo_matching_and_ambiguous_phrases(self) -> None:
        """Correct a clear near miss but do not guess from a longer unrelated phrase."""
        self.assertEqual(parse_command("advan ced").value, "Advanced")
        self.assertEqual(parse_command("pythn").value, "Python")
        self.assertIsNone(parse_command("I heard somebody say something"))
        self.assertIsNone(parse_command("turn around"))

    def test_command_cooldown_applies_to_paraphrases(self) -> None:
        """Suppress repeated intents even when each phrase uses different wording."""
        parser = CommandParser(cooldown_seconds=1.0, clock=lambda: 10.0)
        first = parser.parse("start")
        repeated = parser.parse("start the game")
        self.assertEqual(first.action, "start")
        self.assertIsNone(repeated)
        self.assertTrue(parser.was_suppressed)

    def test_repeated_next_topic_works_after_a_short_pause(self) -> None:
        """Allow learners to advance pages again without waiting a full second."""
        parser = CommandParser(clock=lambda: 0.0)
        first = parser.parse("next topic", now=10.0)
        too_soon = parser.parse("next topic", now=10.2)

        self.assertEqual(first.action, "next")
        self.assertIsNone(too_soon)
        self.assertTrue(parser.was_suppressed)

        second = parser.parse("next topic", now=10.36)
        self.assertEqual(second.action, "next")
        self.assertFalse(parser.was_suppressed)

    def test_cooldown_does_not_block_a_different_intent(self) -> None:
        """Allow a domain or direction command immediately after another action."""
        parser = CommandParser(cooldown_seconds=1.0, clock=lambda: 10.0)
        self.assertEqual(parser.parse("start").action, "start")
        domain = parser.parse("go with Python")
        self.assertEqual((domain.action, domain.value), ("select_domain", "Python"))


if __name__ == "__main__":
    unittest.main()
