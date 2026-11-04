"""Verify the hand-designed course mazes pass route and gate validation."""

import unittest
from dataclasses import replace

from maze.maze_data import all_mazes
from maze.validator import validate_maze


class MazeValidatorTests(unittest.TestCase):
    """Check all course routes and reject a malformed required gate."""

    def test_all_nine_mazes_have_a_route_through_five_required_doors(self) -> None:
        """Every domain and difficulty has one valid, gate-blocked route."""
        layouts = tuple(all_mazes())
        self.assertEqual(len(layouts), 9)
        for layout in layouts:
            with self.subTest(domain=layout.domain, level=layout.level):
                result = validate_maze(layout)
                self.assertTrue(result.valid, result.errors)
                self.assertEqual(len(layout.doors), 5)
                self.assertTrue(result.route)
                self.assertEqual(result.route[0], layout.start)
                self.assertEqual(result.route[-1], layout.finish)
                self.assertTrue(all(position in result.route for position in layout.doors.values()))

    def test_validator_rejects_a_grid_with_a_missing_door(self) -> None:
        """A missing door tile is reported as an invalid maze."""
        layout = next(all_mazes())
        door_position = layout.doors[1]
        grid = list(layout.grid)
        row = list(grid[door_position[1]])
        row[door_position[0]] = "."
        grid[door_position[1]] = "".join(row)

        result = validate_maze(replace(layout, grid=tuple(grid)))

        self.assertFalse(result.valid)
        self.assertTrue(any("door" in error.casefold() for error in result.errors))


if __name__ == "__main__":
    unittest.main()
