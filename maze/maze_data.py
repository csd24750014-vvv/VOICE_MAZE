"""Deterministic, difficulty-scaled perfect mazes for all learning courses."""

import random
from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Iterable, Mapping, Tuple

Position = Tuple[int, int]

WALL = "#"
PATH = "."
START = "S"
FINISH = "F"

_CELL_COUNTS = {
    "beginner": 9,
    "intermediate": 11,
    "advanced": 13,
}
_COURSE_SEEDS: Dict[Tuple[str, str], int] = {
    ("python", "beginner"): 1103,
    ("python", "intermediate"): 1207,
    ("python", "advanced"): 1301,
    ("sql", "beginner"): 2101,
    ("sql", "intermediate"): 2203,
    ("sql", "advanced"): 2309,
    ("logical reasoning", "beginner"): 3109,
    ("logical reasoning", "intermediate"): 3203,
    ("logical reasoning", "advanced"): 3301,
}
_DOMAIN_LABELS = {
    "python": "Python",
    "sql": "SQL",
    "logical reasoning": "Logical Reasoning",
}


@dataclass(frozen=True)
class MazeLayout:
    """Immutable grid, endpoints, five course gates, and unique intended route."""

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


def get_maze(domain: str, level: str) -> MazeLayout:
    """Return a seeded unique-route maze for a domain and difficulty."""
    domain_key = _normalize_domain(domain)
    level_key = level.strip().casefold()
    seed = _COURSE_SEEDS.get((domain_key, level_key))
    if seed is None:
        raise ValueError(f"No maze is defined for domain={domain!r}, level={level!r}.")
    return _generate_layout(_DOMAIN_LABELS[domain_key], level_key.title(), seed)


def all_mazes() -> Iterable[MazeLayout]:
    """Yield the nine deterministic domain and difficulty maze layouts."""
    for (domain, level), seed in _COURSE_SEEDS.items():
        yield _generate_layout(_DOMAIN_LABELS[domain], level.title(), seed)


def _generate_layout(domain: str, level: str, seed: int) -> MazeLayout:
    """Build a randomized spanning-tree maze and place its five topic gates."""
    cell_count = _CELL_COUNTS[level.casefold()]
    width = height = cell_count * 2 + 1
    grid = [[WALL for _ in range(width)] for _ in range(height)]
    start = (1, 1)
    finish = (width - 2, height - 2)
    for cell_y in range(cell_count):
        for cell_x in range(cell_count):
            grid[cell_y * 2 + 1][cell_x * 2 + 1] = PATH

    random_source = random.Random(seed)
    parents: dict[Position, Position | None] = {start: None}
    stack = [start]
    while stack:
        current_x, current_y = stack[-1]
        candidates = [
            (current_x + dx * 2, current_y + dy * 2)
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))
            if 1 <= current_x + dx * 2 < width - 1
            and 1 <= current_y + dy * 2 < height - 1
            and (current_x + dx * 2, current_y + dy * 2) not in parents
        ]
        if not candidates:
            stack.pop()
            continue
        random_source.shuffle(candidates)
        next_cell = candidates[0]
        wall = (
            (current_x + next_cell[0]) // 2,
            (current_y + next_cell[1]) // 2,
        )
        grid[wall[1]][wall[0]] = PATH
        parents[next_cell] = stack[-1]
        stack.append(next_cell)

    cell_route = _reconstruct_cell_route(parents, finish)
    route: list[Position] = []
    for index, cell in enumerate(cell_route):
        if index:
            previous = cell_route[index - 1]
            route.append(((previous[0] + cell[0]) // 2, (previous[1] + cell[1]) // 2))
        route.append(cell)

    doors = _place_doors(route)
    for door_id, (door_x, door_y) in doors.items():
        grid[door_y][door_x] = str(door_id)
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


def _reconstruct_cell_route(
    parents: Mapping[Position, Position | None],
    finish: Position,
) -> list[Position]:
    """Follow DFS parent links from the finish cell back to the entrance."""
    route: list[Position] = []
    current: Position | None = finish
    while current is not None:
        route.append(current)
        current = parents[current]
    route.reverse()
    return route


def _place_doors(route: list[Position]) -> Dict[int, Position]:
    """Space five numbered doors along the unique route, away from endpoints."""
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


def _normalize_domain(domain: str) -> str:
    """Normalize domain spelling while retaining the two-word logic course."""
    normalized = " ".join(domain.casefold().split())
    if normalized in {"logic", "logical"}:
        return "logical reasoning"
    return normalized
