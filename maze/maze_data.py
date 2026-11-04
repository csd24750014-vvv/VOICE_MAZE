"""Hand-designed course routes compiled into compact maze tile grids."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Iterable, Mapping, Tuple

Position = Tuple[int, int]

GRID_WIDTH = 19
GRID_HEIGHT = 19
WALL = "#"
PATH = "."
START = "S"
FINISH = "F"


@dataclass(frozen=True)
class MazeLayout:
    """Immutable grid, endpoints, doors, and intended route for one course."""

    domain: str
    level: str
    grid: Tuple[str, ...]
    start: Position
    finish: Position
    doors: Mapping[int, Position]
    intended_route: Tuple[Position, ...]

    @property
    def width(self) -> int:
        """Return the number of tile columns in the grid."""
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        """Return the number of tile rows in the grid."""
        return len(self.grid)

    def tile_at(self, position: Position) -> str:
        """Return the tile at a grid position, treating outside cells as walls."""
        x, y = position
        if not (0 <= x < self.width and 0 <= y < self.height):
            return WALL
        return self.grid[y][x]


@dataclass(frozen=True)
class _HandDesignedRoute:
    """Human-authored lane endpoints and branch details for a course maze."""

    lane_ends: Tuple[int, int, int, int, int]
    branches: Tuple[Tuple[int, float, str, int], ...]


# End columns describe five horizontal lanes; branch entries identify lane,
# horizontal position ratio, direction, and branch length.
_ROUTES: Dict[Tuple[str, str], _HandDesignedRoute] = {
    ("python", "beginner"): _HandDesignedRoute(
        (17, 1, 14, 2, 17),
        ((1, 0.34, "S", 1),),
    ),
    ("python", "intermediate"): _HandDesignedRoute(
        (15, 3, 17, 1, 17),
        ((1, 0.28, "S", 1), (2, 0.66, "N", 1), (3, 0.48, "S", 2)),
    ),
    ("python", "advanced"): _HandDesignedRoute(
        (13, 5, 17, 3, 17),
        (
            (1, 0.24, "S", 1),
            (1, 0.72, "N", 2),
            (2, 0.34, "S", 2),
            (3, 0.68, "N", 1),
            (3, 0.34, "S", 2),
        ),
    ),
    ("sql", "beginner"): _HandDesignedRoute(
        (17, 4, 1, 15, 17),
        ((2, 0.80, "N", 1),),
    ),
    ("sql", "intermediate"): _HandDesignedRoute(
        (14, 2, 17, 5, 17),
        ((1, 0.30, "N", 1), (2, 0.72, "S", 2), (3, 0.45, "N", 1)),
    ),
    ("sql", "advanced"): _HandDesignedRoute(
        (12, 6, 17, 2, 17),
        (
            (1, 0.72, "S", 2),
            (2, 0.40, "N", 2),
            (2, 0.70, "S", 1),
            (3, 0.30, "N", 2),
            (3, 0.70, "S", 2),
        ),
    ),
    ("logical reasoning", "beginner"): _HandDesignedRoute(
        (17, 2, 15, 1, 17),
        ((1, 0.62, "N", 1),),
    ),
    ("logical reasoning", "intermediate"): _HandDesignedRoute(
        (16, 1, 13, 4, 17),
        ((1, 0.38, "S", 1), (2, 0.52, "N", 1), (3, 0.62, "S", 2)),
    ),
    ("logical reasoning", "advanced"): _HandDesignedRoute(
        (13, 5, 16, 2, 17),
        (
            (1, 0.25, "S", 2),
            (1, 0.68, "N", 1),
            (2, 0.35, "S", 2),
            (3, 0.27, "N", 2),
            (3, 0.72, "S", 1),
        ),
    ),
}

_LANE_ROWS = (1, 5, 9, 13, 17)
_DIRECTIONS: Dict[str, Position] = {
    "N": (0, -1),
    "S": (0, 1),
}


def get_maze(domain: str, level: str) -> MazeLayout:
    """Return the hand-designed maze for a domain and difficulty."""
    key = (_normalize_domain(domain), level.strip().casefold())
    design = _ROUTES.get(key)
    if design is None:
        raise ValueError(f"No maze is defined for domain={domain!r}, level={level!r}.")
    return _compile_layout(domain.strip(), level.strip(), design)


def all_mazes() -> Iterable[MazeLayout]:
    """Return compiled layouts for all nine supported courses."""
    for domain, level in _ROUTES:
        display_domain = {
            "python": "Python",
            "sql": "SQL",
            "logical reasoning": "Logical Reasoning",
        }[domain]
        yield _compile_layout(display_domain, level.title(), _ROUTES[(domain, level)])


def _compile_layout(
    domain: str,
    level: str,
    design: _HandDesignedRoute,
) -> MazeLayout:
    """Rasterize a hand-authored route, its five gates, and its side branches."""
    route: list[Position] = [(1, _LANE_ROWS[0])]
    for lane_index, end_x in enumerate(design.lane_ends):
        y = _LANE_ROWS[lane_index]
        current_x = route[-1][0]
        horizontal = _horizontal_segment(current_x, end_x, y)
        route.extend(horizontal[1:])
        if lane_index + 1 < len(_LANE_ROWS):
            next_y = _LANE_ROWS[lane_index + 1]
            route.extend((end_x, row) for row in range(y + 1, next_y + 1))

    route_positions = set(route)
    if len(route_positions) != len(route):
        raise ValueError(f"Hand-designed {domain} {level} route intersects itself.")

    doors = _place_doors(route)
    walkable = set(route_positions)
    branch_cells = _compile_branches(design, route, walkable)
    walkable.update(branch_cells)

    grid = [[WALL for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    for x, y in walkable:
        grid[y][x] = PATH
    for door_id, (x, y) in doors.items():
        grid[y][x] = str(door_id)

    start = route[0]
    finish = route[-1]
    grid[start[1]][start[0]] = START
    grid[finish[1]][finish[0]] = FINISH
    return MazeLayout(
        domain=domain,
        level=level,
        grid=tuple("".join(row) for row in grid),
        start=start,
        finish=finish,
        doors=MappingProxyType(doors),
        intended_route=tuple(route),
    )


def _horizontal_segment(start_x: int, end_x: int, y: int) -> list[Position]:
    """Return every grid cell along one inclusive horizontal lane segment."""
    step = 1 if end_x >= start_x else -1
    return [(x, y) for x in range(start_x, end_x + step, step)]


def _place_doors(route: list[Position]) -> Dict[int, Position]:
    """Place five ordered doors at evenly spaced non-endpoint route positions."""
    doors: Dict[int, Position] = {}
    for door_id in range(1, 6):
        target = round((door_id / 6) * (len(route) - 1))
        candidate = target
        while candidate in (0, len(route) - 1) or route[candidate] in doors.values():
            candidate += 1
            if candidate >= len(route) - 1:
                candidate = 1
        doors[door_id] = route[candidate]
    return doors


def _compile_branches(
    design: _HandDesignedRoute,
    route: list[Position],
    walkable: set[Position],
) -> set[Position]:
    """Create distinct short dead-end branches without opening door shortcuts."""
    additions: set[Position] = set()
    for lane_index, ratio, direction, length in design.branches:
        if lane_index not in (1, 2, 3) or direction not in _DIRECTIONS:
            raise ValueError("Maze branches must use an interior lane and N/S direction.")
        if not 1 <= length <= 2 or not 0.0 < ratio < 1.0:
            raise ValueError("Maze branches must be one or two cells long.")

        y = _LANE_ROWS[lane_index]
        lane = [position for position in route if position[1] == y]
        anchor_index = min(len(lane) - 1, max(1, round(ratio * (len(lane) - 1))))
        anchor = lane[anchor_index]
        dx, dy = _DIRECTIONS[direction]
        branch: list[Position] = [
            (anchor[0] + dx * step, anchor[1] + dy * step)
            for step in range(1, length + 1)
        ]
        if any(position in walkable or position in additions for position in branch):
            raise ValueError(f"Hand-designed branch at {anchor} overlaps a route.")
        previous = anchor
        branch_so_far: set[Position] = set()
        for position in branch:
            neighbors = {
                (position[0] + offset_x, position[1] + offset_y)
                for offset_x, offset_y in ((1, 0), (-1, 0), (0, 1), (0, -1))
            }
            existing = (walkable | additions | branch_so_far) & neighbors
            if existing != {previous}:
                raise ValueError(
                    f"Hand-designed branch at {anchor} creates an unintended connection."
                )
            branch_so_far.add(position)
            previous = position
        additions.update(branch)
    return additions


def _normalize_domain(domain: str) -> str:
    """Normalize domain spelling while retaining the two-word logic course name."""
    normalized = " ".join(domain.casefold().split())
    if normalized in {"logic", "logical"}:
        return "logical reasoning"
    return normalized
