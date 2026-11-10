"""Verify locked difficulties cannot be opened before course completion."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scenes.level_scene import LevelScene


class LevelProgressionTests(unittest.TestCase):
    """Keep the level-selection screen and direct voice choices progression-safe."""

    def _scene(self, unlocked: frozenset[str]) -> tuple[LevelScene, SimpleNamespace]:
        """Build a level scene with deterministic saved progress and a scene spy."""
        game = SimpleNamespace(
            screen=SimpleNamespace(get_size=lambda: (1440, 810)),
            state=SimpleNamespace(domain="Python", level=None),
            scenes=SimpleNamespace(change=lambda scene: None),
        )
        with patch("scenes.level_scene.unlocked_levels", return_value=unlocked):
            scene = LevelScene(game)
        return scene, game

    def test_only_beginner_is_available_without_completion(self) -> None:
        """A fresh domain exposes Beginner but disables both later levels."""
        scene, _ = self._scene(frozenset({"Beginner"}))

        scene._layout_buttons()

        self.assertEqual(
            [button.enabled for button in scene._buttons],
            [True, False, False],
        )

    def test_voice_selection_cannot_skip_a_locked_difficulty(self) -> None:
        """A direct Advanced selection leaves the course unchanged while locked."""
        scene, game = self._scene(frozenset({"Beginner"}))

        scene._select_level("Advanced")

        self.assertIsNone(game.state.level)
        self.assertIn("Complete Intermediate", scene.toast.message)

    def test_completed_beginner_unlocks_only_intermediate(self) -> None:
        """Advanced stays locked until Intermediate has also been completed."""
        scene, _ = self._scene(frozenset({"Beginner", "Intermediate"}))

        scene._layout_buttons()

        self.assertEqual(
            [button.enabled for button in scene._buttons],
            [True, True, False],
        )


if __name__ == "__main__":
    unittest.main()
