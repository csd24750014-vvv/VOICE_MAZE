"""Verify the learning screens keep voice feedback and controls separated."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from scenes.base_scene import BaseScene
from scenes.level_scene import LevelScene
from scenes.notes_scene import NotesScene
from scenes.revision_scene import RevisionScene
from ui.components import Button, Toast
from ui.theme import draw_text, font, wrap_text


class LearningScreenLayoutTests(unittest.TestCase):
    """Check key lesson and difficulty controls at the minimum window size."""

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize Pygame fonts once for off-screen rendering tests."""
        pygame.font.init()

    def setUp(self) -> None:
        """Create a minimal game context and a 1280-by-720 drawing surface."""
        self.surface = pygame.Surface((1280, 720))
        self.mic_status = SimpleNamespace(
            state="idle",
            snapshot=lambda: SimpleNamespace(state="idle", message=""),
        )
        self.game = SimpleNamespace(
            screen=self.surface,
            state=SimpleNamespace(domain="Python", level="Beginner"),
            mic_status=self.mic_status,
        )

    def test_last_notes_page_does_not_draw_next_topic_button(self) -> None:
        """The final topic page shows start-maze navigation, not next-topic."""
        scene = NotesScene(self.game)
        scene.page_index = 4
        drawn_labels: list[str] = []
        original_draw = Button.draw

        def capture_draw(button: Button, surface: pygame.Surface) -> None:
            drawn_labels.append(button.label)
            original_draw(button, surface)

        with patch.object(Button, "draw", capture_draw):
            scene.draw(self.surface)

        self.assertNotIn("NEXT TOPIC", drawn_labels)
        self.assertIn("START MAZE", drawn_labels)

    def test_level_controls_are_below_level_card_content(self) -> None:
        """Level buttons remain inside their cards without crossing instruction text."""
        with patch(
            "scenes.level_scene.unlocked_levels",
            return_value=frozenset({"Beginner"}),
        ):
            scene = LevelScene(self.game)

        scene.draw(self.surface)

        for button in scene._buttons:
            self.assertEqual(button.rect.height, 50)
            self.assertGreaterEqual(button.rect.top, 400)
            self.assertLessEqual(button.rect.bottom, 500)
        self.assertEqual(
            [button.enabled for button in scene._buttons],
            [True, False, False],
        )

    def test_level_cards_show_the_current_maze_sizes(self) -> None:
        """Difficulty cards match the compact cell counts used by the game."""
        with patch(
            "scenes.level_scene.unlocked_levels",
            return_value=frozenset({"Beginner"}),
        ):
            scene = LevelScene(self.game)
        rendered_text: list[str] = []
        original_draw_text = draw_text

        def capture_text(*args: object, **kwargs: object) -> pygame.Rect:
            rendered_text.append(str(args[1]))
            return original_draw_text(*args, **kwargs)

        with patch("scenes.level_scene.draw_text", side_effect=capture_text):
            scene.draw(self.surface)

        self.assertIn("5 × 5 cells  •  5 topic doors", rendered_text)
        self.assertIn("7 × 7 cells  •  5 topic doors", rendered_text)
        self.assertIn("9 × 9 cells  •  5 topic doors", rendered_text)

    def test_revision_notes_and_code_fit_inside_their_panels(self) -> None:
        """Long revision text is wrapped or fitted instead of overflowing."""
        scene = RevisionScene(
            self.game,
            {
                "title": "Variables",
                "notes": [
                    "A long learning note " * 12,
                    "Another long learning note " * 12,
                    "A third long learning note " * 12,
                    "A fourth long learning note " * 12,
                    "A fifth long learning note " * 12,
                ],
                "example": "result = " + "some_long_value " * 18,
            },
            wrong_question="Which value is stored?",
            explanation="The variable name refers to the value stored in memory.",
            retry_available=True,
            on_retry=lambda: None,
            on_results=lambda: None,
            on_cancel=lambda: None,
        )
        drawn_bounds: list[pygame.Rect] = []
        original_draw_text = draw_text

        def capture_text(*args: object, **kwargs: object) -> pygame.Rect:
            bounds = original_draw_text(*args, **kwargs)
            drawn_bounds.append(bounds)
            return bounds

        with patch("scenes.revision_scene.draw_text", side_effect=capture_text):
            scene.draw(self.surface)

        self.assertTrue(drawn_bounds)
        self.assertTrue(
            all(
                0 <= bounds.left <= bounds.right <= self.surface.get_width()
                and 0 <= bounds.top <= bounds.bottom <= self.surface.get_height()
                for bounds in drawn_bounds
            )
        )

    def test_voice_caption_and_error_have_separate_footer_panels(self) -> None:
        """Microphone errors do not share or overwrite the recognized-speech panel."""
        self.mic_status.state = "error"
        self.mic_status.snapshot = lambda: SimpleNamespace(
            state="error",
            message="Microphone unavailable. Use the mouse to keep playing.",
        )
        scene = BaseScene(self.game)
        scene.caption = "Review all topics"
        scene.toast.show("Say that again")
        with (
            patch("scenes.base_scene.draw_rounded_rect") as rounded_rect,
            patch.object(scene.toast, "draw", wraps=scene.toast.draw) as toast_draw,
        ):
            scene.draw_shell(self.surface, "Test", "Test", "Test")
            panel_rects = [
                call.args[1]
                for call in rounded_rect.call_args_list
                if isinstance(call.args[1], pygame.Rect)
            ]

        footer_panels = [
            rect
            for rect in panel_rects
            if rect.top == self.surface.get_height() - 57
        ]
        self.assertEqual(len(footer_panels), 2)
        self.assertFalse(footer_panels[0].colliderect(footer_panels[1]))
        toast_rect = toast_draw.call_args.args[1]
        self.assertFalse(footer_panels[0].colliderect(toast_rect))
        self.assertFalse(footer_panels[1].colliderect(toast_rect))
        self.assertTrue(scene.toast.visible)

    def test_long_button_labels_and_toasts_stay_within_their_bounds(self) -> None:
        """Wrapped voice and option text remains inside its own UI component."""
        self.assertTrue(
            all(
                font(14).size(line)[0] <= 180
                for line in wrap_text(
                    "A very long quiz answer that needs a clean wrap",
                    font(14),
                    180,
                )
            )
        )
        text_bounds: list[pygame.Rect] = []
        original_draw_text = draw_text

        def capture_text(*args: object, **kwargs: object) -> pygame.Rect:
            bounds = original_draw_text(*args, **kwargs)
            text_bounds.append(bounds)
            return bounds

        button_rect = pygame.Rect(200, 200, 360, 48)
        button = Button(
            button_rect,
            "A very long quiz answer that must never overflow the button",
        )
        toast_rect = pygame.Rect(800, 82, 420, 52)
        toast = Toast()
        toast.show(
            "I heard you, but that action is not available here. "
            "Try one of the on-screen commands."
        )
        with patch("ui.components.draw_text", side_effect=capture_text):
            button.draw(self.surface)
            button_text_bounds = text_bounds[:]
            text_bounds.clear()
            toast.draw(self.surface, toast_rect)

        self.assertTrue(button_text_bounds)
        self.assertTrue(all(button_rect.contains(bounds) for bounds in button_text_bounds))
        self.assertTrue(text_bounds)
        self.assertTrue(all(toast_rect.contains(bounds) for bounds in text_bounds))

    def test_toast_avoids_the_heading_area_at_minimum_window_size(self) -> None:
        """A long screen title remains separate from the top-right voice toast."""
        scene = BaseScene(self.game)
        scene.toast.show("A long voice status message that wraps onto two lines.")
        draw_bounds: list[pygame.Rect] = []
        original_draw_text = draw_text

        def capture_text(*args: object, **kwargs: object) -> pygame.Rect:
            bounds = original_draw_text(*args, **kwargs)
            draw_bounds.append(bounds)
            return bounds

        with (
            patch("scenes.base_scene.draw_text", side_effect=capture_text),
            patch.object(scene.toast, "draw", wraps=scene.toast.draw) as toast_draw,
        ):
            scene.draw_shell(
                self.surface,
                "RESULTS",
                "A particularly long title that should not touch the voice indicator",
                "A longer subtitle that should wrap without crossing over the toast.",
                draw_background=False,
            )

        toast_rect = toast_draw.call_args.args[1]
        title_bounds = draw_bounds[1]
        self.assertFalse(title_bounds.colliderect(toast_rect))
        self.assertGreaterEqual(toast_rect.top, 82)


if __name__ == "__main__":
    unittest.main()
