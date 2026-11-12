"""Testable player movement, wall collision, and locked-door behavior."""

from dataclasses import dataclass
from math import isfinite
from typing import Dict, Optional

from maze.maze_data import FINISH, MazeLayout, Position

_MOVEMENTS: Dict[str, Position] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


@dataclass(frozen=True)
class MoveResult:
    """Describe a movement request and how many tiles it traversed."""

    status: str
    position: Position
    door_id: Optional[int] = None
    steps: int = 0


class MazeEngine:
    """Own mutable player location and unlocked doors for a fixed maze layout."""

    def __init__(self, layout: MazeLayout) -> None:
        """Place the player at the start and lock all five door tiles."""
        self.layout = layout
        self.player_position = layout.start
        self._unlocked_doors: set[int] = set()

    @property
    def unlocked_doors(self) -> frozenset[int]:
        """Return a read-only view of the doors already opened."""
        return frozenset(self._unlocked_doors)

    @property
    def doors_unlocked(self) -> int:
        """Return the number of unlocked doors in this maze."""
        return len(self._unlocked_doors)

    @property
    def finished(self) -> bool:
        """Report whether the player has reached the finish marker."""
        return self.layout.tile_at(self.player_position) == FINISH

    def move(self, direction: str) -> MoveResult:
        """Move one tile if possible, reporting walls and locked doors clearly."""
        if self.finished:
            return MoveResult("finish", self.player_position)
        normalized_direction = direction.casefold().strip()
        movement = _MOVEMENTS.get(normalized_direction)
        if movement is None:
            raise ValueError(f"Unknown movement direction: {direction!r}.")
        destination = (
            self.player_position[0] + movement[0],
            self.player_position[1] + movement[1],
        )
        tile = self.layout.tile_at(destination)
        if tile == "#":
            return MoveResult("wall", self.player_position)
        if tile in "12345":
            door_id = int(tile)
            if door_id not in self._unlocked_doors:
                return MoveResult("locked_door", self.player_position, door_id)
        self.player_position = destination
        return MoveResult(
            "finish" if self.finished else "moved",
            self.player_position,
        )

    def move_until_decision(self, direction: str) -> MoveResult:
        """Follow a straight corridor until blocked, gated, finished, or at a junction."""
        normalized_direction = direction.casefold().strip()
        if normalized_direction not in _MOVEMENTS:
            raise ValueError(f"Unknown movement direction: {direction!r}.")

        steps = 0
        while True:
            result = self.move(normalized_direction)
            if result.status == "wall":
                if steps:
                    return MoveResult("moved", self.player_position, steps=steps)
                return result
            if result.status == "locked_door":
                return MoveResult(
                    "locked_door",
                    self.player_position,
                    result.door_id,
                    steps,
                )
            steps += 1
            if result.status == "finish":
                return MoveResult("finish", self.player_position, steps=steps)
            if len(self.available_directions()) >= 3:
                return MoveResult("junction", self.player_position, steps=steps)

    def available_directions(self) -> tuple[str, ...]:
        """Return directions that lead to a path, including a locked door."""
        directions: list[str] = []
        for direction, movement in _MOVEMENTS.items():
            destination = (
                self.player_position[0] + movement[0],
                self.player_position[1] + movement[1],
            )
            if self.layout.tile_at(destination) != "#":
                directions.append(direction)
        return tuple(directions)

    def unlock_door(self, door_id: int) -> None:
        """Remove a completed gate and step onto it when the player is adjacent."""
        if isinstance(door_id, bool) or door_id not in self.layout.doors:
            raise ValueError(f"Maze has no door numbered {door_id}.")
        self._unlocked_doors.add(door_id)
        door_position = self.layout.doors[door_id]
        if sum(
            abs(current - target)
            for current, target in zip(self.player_position, door_position)
        ) == 1:
            self.player_position = door_position

    def reset(self) -> None:
        """Restore the start position and relock every course door."""
        self.player_position = self.layout.start
        self._unlocked_doors.clear()
