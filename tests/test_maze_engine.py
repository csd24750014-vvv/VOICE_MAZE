"""Verify corridor movement stops safely at junctions and locked doors."""

import unittest

from maze.maze_data import MazeLayout, all_mazes
from maze.maze_engine import MazeEngine


_DIRECTION_BY_DELTA = {
    (0, -1): "up",
    (0, 1): "down",
    (-1, 0): "left",
    (1, 0): "right",
}


class CorridorMovementTests(unittest.TestCase):
    """Keep long directional moves inside the intended corridor segments."""

    def test_corridor_movement_stops_at_each_layout_junction(self) -> None:
        """A long command traverses a corridor, but never passes a junction."""
        for layout in all_mazes():
            with self.subTest(domain=layout.domain, level=layout.level):
                engine = MazeEngine(layout)
                approach = _longest_junction_approach(layout)
                self.assertIsNotNone(approach, "Each layout should contain a decision point.")
                steps, junction, start, direction = approach
                self.assertGreater(steps, 1, "The test must traverse a real corridor.")
                engine.player_position = start

                result = engine.move_until_decision(direction)

                self.assertEqual(result.status, "junction")
                self.assertEqual(result.position, junction)
                self.assertEqual(result.steps, steps)
                self.assertEqual(len(engine.available_directions()), 3)

    def test_locked_door_interrupts_a_corridor_move(self) -> None:
        """The engine reports a locked gate instead of moving through it."""
        for layout in all_mazes():
            with self.subTest(domain=layout.domain, level=layout.level):
                engine = MazeEngine(layout)
                door_id = min(layout.doors)
                door_position = layout.doors[door_id]
                route_index = layout.intended_route.index(door_position)
                predecessor = layout.intended_route[route_index - 1]
                delta = (door_position[0] - predecessor[0], door_position[1] - predecessor[1])
                engine.player_position = predecessor

                result = engine.move_until_decision(_DIRECTION_BY_DELTA[delta])

                self.assertEqual(result.status, "locked_door")
                self.assertEqual(result.door_id, door_id)
                self.assertEqual(result.position, predecessor)
                self.assertNotEqual(result.position, door_position)

    def test_move_stops_at_wall_without_leaving_the_maze(self) -> None:
        """A move into a wall leaves the player at the edge of its branch."""
        for layout in all_mazes():
            with self.subTest(domain=layout.domain, level=layout.level):
                engine = MazeEngine(layout)
                branch_tip = next(
                    (x, y)
                    for y, row in enumerate(layout.grid)
                    for x, tile in enumerate(row)
                    if tile == "." and len(_walkable_neighbors(layout, (x, y))) == 1
                )
                engine.player_position = branch_tip
                neighbor = _walkable_neighbors(layout, branch_tip)[0]
                dx = branch_tip[0] - neighbor[0]
                dy = branch_tip[1] - neighbor[1]

                result = engine.move_until_decision(_DIRECTION_BY_DELTA[(dx, dy)])

                self.assertEqual(result.position, branch_tip)
                self.assertEqual(result.status, "wall")


def _walkable_neighbors(layout: MazeLayout, position: tuple[int, int]) -> list[tuple[int, int]]:
    """Return neighboring non-wall cells for a compiled maze layout."""
    x, y = position
    neighbors = []
    for candidate in ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)):
        if layout.tile_at(candidate) != "#":
            neighbors.append(candidate)
    return neighbors


def _longest_junction_approach(
    layout: MazeLayout,
) -> tuple[int, tuple[int, int], tuple[int, int], str] | None:
    """Find a straight walkable corridor leading into a junction."""
    best = None
    for y, row in enumerate(layout.grid):
        for x, tile in enumerate(row):
            junction = (x, y)
            if (
                tile == "#"
                or junction in layout.doors.values()
                or len(_walkable_neighbors(layout, junction)) < 3
            ):
                continue
            for predecessor in _walkable_neighbors(layout, junction):
                if (
                    predecessor in layout.doors.values()
                    or len(_walkable_neighbors(layout, predecessor)) >= 3
                ):
                    continue
                delta = (junction[0] - predecessor[0], junction[1] - predecessor[1])
                direction = _DIRECTION_BY_DELTA[delta]
                start = predecessor
                steps = 1
                while steps < 5:
                    candidate = (start[0] - delta[0], start[1] - delta[1])
                    if (
                        layout.tile_at(candidate) == "#"
                        or candidate in layout.doors.values()
                        or len(_walkable_neighbors(layout, candidate)) >= 3
                    ):
                        break
                    start = candidate
                    steps += 1
                if best is None or steps > best[0]:
                    best = (steps, junction, start, direction)
    return best


if __name__ == "__main__":
    unittest.main()
