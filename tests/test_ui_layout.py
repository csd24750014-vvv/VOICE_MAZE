"""Verify the learning screens keep voice feedback and controls separated."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from scenes.base_scene import BaseScene
from scenes.level_scene import LevelScene
from scenes.notes_scene import NotesScene
from ui.components import Button


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


if __name__ == "__main__":
    unittest.main()
