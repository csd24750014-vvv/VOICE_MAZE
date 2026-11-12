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
                self.assertTrue(result.unique_route)
                self.assertEqual(len(layout.doors), 5)
                self.assertTrue(result.route)
                self.assertEqual(result.route[0], layout.start)
                self.assertEqual(result.route[-1], layout.finish)
                self.assertTrue(all(position in result.route for position in layout.doors.values()))

    def test_maze_size_grows_with_each_difficulty(self) -> None:
        """Maze size and route complexity increase at every level for each domain."""
        for domain in ("Python", "SQL", "Logical Reasoning"):
            layouts = [
                layout
                for layout in all_mazes()
                if layout.domain == domain
            ]
            layouts.sort(key=lambda layout: ("Beginner", "Intermediate", "Advanced").index(layout.level))
            self.assertEqual(
                [layout.width for layout in layouts],
                [11, 15, 19],
            )
            route_lengths = [len(layout.intended_route) for layout in layouts]
            self.assertLess(route_lengths[0], route_lengths[1])
            self.assertLess(route_lengths[1], route_lengths[2])
            junction_counts = [
                sum(
                    sum(
                        layout.tile_at((x + dx, y + dy)) != "#"
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    ) >= 3
                    for y, row in enumerate(layout.grid)
                    for x, tile in enumerate(row)
                    if tile != "#"
                )
                for layout in layouts
            ]
            self.assertLess(junction_counts[0], junction_counts[1])
            self.assertLess(junction_counts[1], junction_counts[2])
            turn_counts = [
                sum(
                    (
                        layout.intended_route[index][0]
                        - layout.intended_route[index - 1][0],
                        layout.intended_route[index][1]
                        - layout.intended_route[index - 1][1],
                    )
                    != (
                        layout.intended_route[index + 1][0]
                        - layout.intended_route[index][0],
                        layout.intended_route[index + 1][1]
                        - layout.intended_route[index][1],
                    )
                    for index in range(1, len(layout.intended_route) - 1)
                )
                for layout in layouts
            ]
            self.assertLess(turn_counts[0], turn_counts[1])
            self.assertLess(turn_counts[1], turn_counts[2])

    def test_all_nine_course_grids_are_distinct(self) -> None:
        """Each domain and difficulty receives its own recognizable layout."""
        layouts = tuple(all_mazes())

        self.assertEqual(len(layouts), 9)
        self.assertEqual(len({layout.grid for layout in layouts}), 9)

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

    def test_validator_rejects_a_loop_that_creates_a_second_route(self) -> None:
        """Opening a wall between existing corridors invalidates uniqueness."""
        layout = next(all_mazes())
        grid = [list(row) for row in layout.grid]
        extra_connection = next(
            (x, y)
            for y, row in enumerate(layout.grid)
            for x, tile in enumerate(row)
            if tile == "#"
            and sum(
                layout.tile_at((x + dx, y + dy)) != "#"
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ) >= 2
        )
        grid[extra_connection[1]][extra_connection[0]] = "."

        result = validate_maze(replace(layout, grid=tuple("".join(row) for row in grid)))

        self.assertFalse(result.valid)
        self.assertFalse(result.unique_route)
        self.assertTrue(any("unique route" in error.casefold() for error in result.errors))


if __name__ == "__main__":
    unittest.main()
