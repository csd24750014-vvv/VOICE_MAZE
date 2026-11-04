"""Breadth-first maze validation for endpoints and required door placement."""

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from maze.maze_data import FINISH, START, WALL, MazeLayout, Position

_NEIGHBORS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass(frozen=True)
class ValidationResult:
    """Report a layout's structural errors and its found start-to-finish route."""

    valid: bool
    errors: Tuple[str, ...]
    route: Tuple[Position, ...] = ()


def validate_maze(layout: MazeLayout) -> ValidationResult:
    """Check grid shape, endpoints, five doors, and a route through every door."""
    errors: list[str] = []
    if not layout.grid or any(len(row) != layout.width for row in layout.grid):
        errors.append("Maze grid must be non-empty and rectangular.")
        return ValidationResult(False, tuple(errors))

    starts = [
        (x, y)
        for y, row in enumerate(layout.grid)
        for x, tile in enumerate(row)
        if tile == START
    ]
    finishes = [
        (x, y)
        for y, row in enumerate(layout.grid)
        for x, tile in enumerate(row)
        if tile == FINISH
    ]
    if starts != [layout.start]:
        errors.append("Grid must contain exactly one start at the declared position.")
    if finishes != [layout.finish]:
        errors.append("Grid must contain exactly one finish at the declared position.")

    valid_tiles = set("#.SF12345")
    if any(tile not in valid_tiles for row in layout.grid for tile in row):
        errors.append("Grid contains an unsupported tile marker.")
    door_counts = {
        door_id: sum(row.count(str(door_id)) for row in layout.grid)
        for door_id in range(1, 6)
    }
    if any(count != 1 for count in door_counts.values()):
        errors.append("Grid must contain exactly one of each door numbered 1 through 5.")
    grid_doors = {
        int(tile): (x, y)
        for y, row in enumerate(layout.grid)
        for x, tile in enumerate(row)
        if tile in "12345"
    }
    if grid_doors != layout.doors:
        errors.append("Door coordinates must match the grid door tiles.")
    if not _is_open(layout, layout.start) or not _is_open(layout, layout.finish):
        errors.append("Start and finish must be traversable positions.")

    route = _find_path(layout, layout.start, layout.finish)
    if route is None:
        errors.append("Start cannot reach finish.")
        return ValidationResult(False, tuple(errors))
    route_set = set(route)
    for door_id in range(1, 6):
        door_position = layout.doors.get(door_id)
        if door_position is None or door_position not in route_set:
            errors.append(f"Door {door_id} does not sit on a start-to-finish route.")
        elif _find_path(layout, layout.start, layout.finish, blocked=door_position):
            errors.append(f"Door {door_id} can be bypassed on the way to the finish.")

    if not _route_is_contiguous(layout.intended_route):
        errors.append("The authored intended route contains a gap.")
    if layout.intended_route:
        intended_set = set(layout.intended_route)
        for door_id, position in layout.doors.items():
            if position not in intended_set:
                errors.append(f"Door {door_id} is missing from the authored intended route.")

    return ValidationResult(not errors, tuple(errors), tuple(route))


def is_valid_maze(layout: MazeLayout) -> bool:
    """Return whether a maze passes all structural and route checks."""
    return validate_maze(layout).valid


def _find_path(
    layout: MazeLayout,
    start: Position,
    finish: Position,
    blocked: Optional[Position] = None,
) -> Optional[Tuple[Position, ...]]:
    """Find a shortest walkable route while optionally treating one cell as wall."""
    if not _is_open(layout, start) or not _is_open(layout, finish) or start == blocked:
        return None
    queue = deque([start])
    parents: dict[Position, Optional[Position]] = {start: None}
    while queue:
        current = queue.popleft()
        if current == finish:
            return _reconstruct_path(parents, finish)
        for dx, dy in _NEIGHBORS:
            neighbor = (current[0] + dx, current[1] + dy)
            if neighbor in parents or neighbor == blocked or not _is_open(layout, neighbor):
                continue
            parents[neighbor] = current
            queue.append(neighbor)
    return None


def _is_open(layout: MazeLayout, position: Position) -> bool:
    """Return whether a tile is inside the grid and not a wall."""
    x, y = position
    return (
        0 <= x < layout.width
        and 0 <= y < layout.height
        and layout.grid[y][x] != WALL
    )


def _reconstruct_path(
    parents: dict[Position, Optional[Position]],
    finish: Position,
) -> Tuple[Position, ...]:
    """Walk predecessor links backward and return a start-to-finish path."""
    path: list[Position] = []
    current: Optional[Position] = finish
    while current is not None:
        path.append(current)
        current = parents[current]
    path.reverse()
    return tuple(path)


def _route_is_contiguous(route: Iterable[Position]) -> bool:
    """Report whether every consecutive authored route tile is cardinally adjacent."""
    positions = list(route)
    return all(
        abs(left[0] - right[0]) + abs(left[1] - right[1]) == 1
        for left, right in zip(positions, positions[1:])
    )
