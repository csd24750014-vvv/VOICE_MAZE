"""Playable grid maze with voice movement, mouse controls, and door gates."""

import math
import time
from typing import TYPE_CHECKING, Optional

import pygame

import config
from maze.maze_data import FINISH, START, WALL, MazeLayout, get_maze
from maze.maze_engine import MazeEngine
from maze.validator import validate_maze
from scenes.base_scene import BaseScene
from ui.components import Button, ProgressBar
from ui.effects import draw_glow, screen_shake_offset
from ui.theme import COLORS, draw_rounded_rect, draw_text
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game

_DIRECTION_ACTIONS = {
    "move_up": "up",
    "move_down": "down",
    "move_left": "left",
    "move_right": "right",
}


class MazeScene(BaseScene):
    """Render a course route and accept voice or mouse corridor movements."""

    def __init__(self, game: "Game") -> None:
        """Load and validate the selected layout and initialize its player."""
        super().__init__(game)
        domain = game.state.domain
        level = game.state.level
        if domain is None or level is None:
            raise ValueError("Select a domain and difficulty before starting the maze.")
        self.layout: MazeLayout = get_maze(domain, level)
        validation = validate_maze(self.layout)
        if not validation.valid:
            details = "; ".join(validation.errors)
            raise ValueError(f"Invalid {domain} {level} maze: {details}")

        self.engine = MazeEngine(self.layout)
        self.started_at = time.monotonic()
        game.state.run_started_at = self.started_at
        self.elapsed_seconds = 0.0
        self._animation_time = 0.0
        self._shake_elapsed = 0.0
        self._shake_active = False
        self._pending_door: Optional[int] = None
        self._dpad: dict[str, Button] = {}
        self._back_button = Button(pygame.Rect(0, 0, 150, 44), "LEARNING NOTES", COLORS["text_muted"])

    def handle_command(self, command: VoiceCommand) -> None:
        """Map voice movement actions onto the four maze directions."""
        if command.action in _DIRECTION_ACTIONS:
            self._move(_DIRECTION_ACTIONS[command.action])
        elif command.action == "back":
            from scenes.notes_scene import NotesScene

            self.game.scenes.change(NotesScene(self.game))

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle D-pad clicks and optional debug-only arrow key movement."""
        self._layout_controls()
        if event.type == pygame.KEYDOWN and config.DEBUG_KEYBOARD_ENABLED:
            key_directions = {
                pygame.K_UP: "up",
                pygame.K_DOWN: "down",
                pygame.K_LEFT: "left",
                pygame.K_RIGHT: "right",
            }
            direction = key_directions.get(event.key)
            if direction is not None:
                self._move(direction)
                return
        if self._back_button.handle_event(event):
            from scenes.notes_scene import NotesScene

            self.game.scenes.change(NotesScene(self.game))
            return
        for direction, button in self._dpad.items():
            if button.handle_event(event):
                self._move(direction)
                return

    def update(self, delta_seconds: float) -> None:
        """Advance the run timer and process non-blocking microphone messages."""
        self.elapsed_seconds = max(0.0, time.monotonic() - self.started_at)
        self.game.state.elapsed_seconds = self.elapsed_seconds
        self._animation_time += delta_seconds
        if self._shake_active:
            self._shake_elapsed += delta_seconds
            if self._shake_elapsed >= 0.18:
                self._shake_active = False
        super().update(delta_seconds)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the tiled map, HUD, player, microphone, and spoken caption."""
        target = surface
        offset = (0, 0)
        if self._shake_active:
            offset = screen_shake_offset(self._shake_elapsed)
            if offset != (0, 0):
                target = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self.draw_shell(
            target,
            "Play  •  Voice controlled maze",
            f"{self.layout.domain} / {self.layout.level}",
            "Speak naturally: “go up”, “turn left”, “move me right”, or “head down”.",
        )
        self._draw_board(target)
        self._draw_hud(target)
        self.draw_shell(
            target,
            "Play  •  Voice controlled maze",
            f"{self.layout.domain} / {self.layout.level}",
            "Speak naturally: “go up”, “turn left”, “move me right”, or “head down”.",
            draw_background=False,
        )
        if target is not surface:
            surface.fill(COLORS["background"])
            surface.blit(target, offset)

    def on_door_unlocked(self, door_id: int) -> None:
        """Unlock a completed topic gate after the challenge scene reports success."""
        if door_id not in self.layout.doors:
            raise ValueError(f"Maze has no door numbered {door_id}.")
        self.engine.unlock_door(door_id)
        self.game.state.doors_unlocked = self.engine.doors_unlocked
        self._pending_door = None
        self.toast.show(f"Door {door_id} unlocked — keep going!", COLORS["green"])

    def _draw_board(self, surface: pygame.Surface) -> None:
        """Render walls, open paths, five animated doors, and the glowing player."""
        width, height = surface.get_size()
        cell_size = max(
            1,
            min(29, (height - 240) // self.layout.height, (width - 570) // self.layout.width),
        )
        board_width = cell_size * self.layout.width
        board_height = cell_size * self.layout.height
        board_x = 56
        board_y = max(158, (height - board_height) // 2 + 20)
        board_rect = pygame.Rect(board_x - 8, board_y - 8, board_width + 16, board_height + 16)
        draw_rounded_rect(
            surface,
            board_rect,
            (9, 12, 24),
            radius=17,
            border_color=COLORS["border"],
            border_width=2,
        )
        glow_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for y, row in enumerate(self.layout.grid):
            for x, tile in enumerate(row):
                rect = pygame.Rect(
                    board_x + x * cell_size + 1,
                    board_y + y * cell_size + 1,
                    cell_size - 2,
                    cell_size - 2,
                )
                if tile == WALL:
                    self._draw_wall(surface, rect)
                else:
                    floor_color = (19, 25, 43) if (x + y) % 2 == 0 else (22, 29, 49)
                    pygame.draw.rect(surface, floor_color, rect, border_radius=4)
                    if tile in "12345" and int(tile) not in self.engine.unlocked_doors:
                        self._draw_door(surface, glow_surface, rect, int(tile), cell_size)
                    elif tile == START:
                        pygame.draw.circle(
                            surface,
                            COLORS["green"],
                            rect.center,
                            max(3, cell_size // 6),
                        )
                    elif tile == FINISH:
                        self._draw_finish(surface, glow_surface, rect, cell_size)
        self._draw_player(surface, glow_surface, board_x, board_y, cell_size)
        surface.blit(glow_surface, (0, 0))

    def _draw_wall(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Give each stone wall tile a subtly highlighted surface."""
        pygame.draw.rect(surface, (39, 48, 73), rect, border_radius=5)
        highlight = pygame.Rect(rect.x + 3, rect.y + 2, max(1, rect.width - 6), 2)
        pygame.draw.rect(surface, (65, 77, 111), highlight, border_radius=2)

    def _draw_door(
        self,
        surface: pygame.Surface,
        glow_surface: pygame.Surface,
        rect: pygame.Rect,
        door_id: int,
        cell_size: int,
    ) -> None:
        """Show a numbered lock tile with a pulse while it remains locked."""
        unlocked = door_id in self.engine.unlocked_doors
        pulse = (math.sin(self._animation_time * 3.2 + door_id) + 1.0) / 2.0
        accent = COLORS["green"] if unlocked else (
            COLORS["cyan"] if door_id % 2 else COLORS["purple"]
        )
        if not unlocked:
            radius = max(5, int(cell_size * (0.44 + pulse * 0.1)))
            pygame.draw.circle(glow_surface, (*accent, 32), rect.center, radius)
        door = pygame.Rect(
            rect.x + max(3, cell_size // 5),
            rect.y + max(2, cell_size // 7),
            max(8, cell_size - max(6, cell_size // 2)),
            max(10, cell_size - max(4, cell_size // 4)),
        )
        draw_rounded_rect(
            surface,
            door,
            (24, 48, 67) if not unlocked else (25, 76, 62),
            radius=4,
            border_color=accent,
            border_width=2,
        )
        shackle_rect = pygame.Rect(
            rect.centerx - max(3, cell_size // 7),
            rect.y + max(2, cell_size // 8),
            max(6, cell_size // 3),
            max(6, cell_size // 3),
        )
        pygame.draw.arc(surface, accent, shackle_rect, math.pi, 2 * math.pi, 2)
        draw_text(
            surface,
            str(door_id),
            (rect.centerx, rect.centery + 3),
            size=max(10, cell_size // 3),
            color=COLORS["text"],
            role="heading",
            align="center",
        )

    def _draw_finish(
        self,
        surface: pygame.Surface,
        glow_surface: pygame.Surface,
        rect: pygame.Rect,
        cell_size: int,
    ) -> None:
        """Draw a glowing finish beacon at the end of the course route."""
        pulse = (math.sin(self._animation_time * 4.0) + 1.0) / 2.0
        radius = max(6, int(cell_size * (0.48 + pulse * 0.12)))
        pygame.draw.circle(glow_surface, (*COLORS["purple"], 48), rect.center, radius + 5)
        pygame.draw.circle(surface, COLORS["purple"], rect.center, radius // 2 + 2)
        draw_text(
            surface,
            "F",
            rect.center,
            size=max(10, cell_size // 3),
            color=COLORS["text"],
            role="heading",
            align="center",
        )

    def _draw_player(
        self,
        surface: pygame.Surface,
        glow_surface: pygame.Surface,
        board_x: int,
        board_y: int,
        cell_size: int,
    ) -> None:
        """Draw the player marker above its current tile with a soft cyan aura."""
        x, y = self.engine.player_position
        center = (
            board_x + x * cell_size + cell_size // 2,
            board_y + y * cell_size + cell_size // 2,
        )
        radius = max(5, cell_size // 3)
        draw_glow(glow_surface, center, radius, COLORS["cyan"])
        pygame.draw.circle(surface, COLORS["cyan"], center, radius)
        pygame.draw.circle(
            surface,
            COLORS["text"],
            (center[0] - max(1, radius // 3), center[1] - max(1, radius // 3)),
            max(2, radius // 3),
        )

    def _draw_hud(self, surface: pygame.Surface) -> None:
        """Show elapsed time, attempts, gate progress, and directional controls."""
        width, height = surface.get_size()
        cell_size = max(
            1,
            min(29, (height - 240) // self.layout.height, (width - 570) // self.layout.width),
        )
        board_x = 56
        sidebar_x = board_x + cell_size * self.layout.width + 42
        sidebar_width = width - sidebar_x - 52
        info_y = 178
        self._draw_stat(
            surface,
            pygame.Rect(sidebar_x, info_y, sidebar_width, 72),
            "TIME IN MAZE",
            _format_time(self.elapsed_seconds),
            COLORS["cyan"],
        )
        self._draw_stat(
            surface,
            pygame.Rect(sidebar_x, info_y + 88, sidebar_width, 72),
            "ATTEMPT",
            (
                f"{min(self.game.state.attempt_limit, max(1, self.game.state.attempts_used + 1))}"
                f" / {self.game.state.attempt_limit}"
            ),
            COLORS["purple"],
        )
        self._draw_stat(
            surface,
            pygame.Rect(sidebar_x, info_y + 176, sidebar_width, 92),
            "TOPIC DOORS",
            f"{self.engine.doors_unlocked} / 5 unlocked",
            COLORS["green"],
        )
        bar = ProgressBar(
            pygame.Rect(sidebar_x + 20, info_y + 244, max(1, sidebar_width - 40), 9),
            self.engine.doors_unlocked,
            5,
            COLORS["green"],
        )
        bar.draw(surface)
        self._layout_controls()
        for button in self._dpad.values():
            button.draw(surface)
        self._back_button.rect.topleft = (sidebar_x, min(height - 112, info_y + 440))
        self._back_button.draw(surface)
        draw_text(
            surface,
            "Locked gates are marked 1–5. Stop at a gate to answer its topic quiz.",
            (sidebar_x, info_y + 270),
            size=14,
            color=COLORS["text_muted"],
        )

    def _draw_stat(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        value: str,
        accent: tuple[int, int, int],
    ) -> None:
        """Draw one dark HUD card with a colored label and large value."""
        draw_rounded_rect(
            surface,
            rect,
            COLORS["surface"],
            radius=14,
            border_color=COLORS["border"],
        )
        draw_text(
            surface,
            label,
            (rect.x + 18, rect.y + 12),
            size=11,
            color=accent,
            role="heading",
        )
        draw_text(
            surface,
            value,
            (rect.x + 18, rect.y + 34),
            size=22,
            color=COLORS["text"],
            role="heading",
        )

    def _layout_controls(self) -> None:
        """Position persistent D-pad buttons inside the HUD sidebar."""
        width, height = self.game.screen.get_size()
        cell_size = max(
            1,
            min(29, (height - 240) // self.layout.height, (width - 570) // self.layout.width),
        )
        sidebar_x = 56 + cell_size * self.layout.width + 42
        sidebar_width = width - sidebar_x - 52
        button_size = min(62, max(46, (sidebar_width - 24) // 3))
        gap = 8
        total_width = button_size * 3 + gap * 2
        start_x = sidebar_x + max(0, (sidebar_width - total_width) // 2)
        start_y = 476
        positions = {
            "up": (start_x + button_size + gap, start_y),
            "left": (start_x, start_y + button_size + gap),
            "down": (start_x + button_size + gap, start_y + button_size + gap),
            "right": (start_x + 2 * (button_size + gap), start_y + button_size + gap),
        }
        if not self._dpad:
            self._dpad = {
                direction: Button(
                    pygame.Rect(position, (button_size, button_size)),
                    {"up": "↑", "down": "↓", "left": "←", "right": "→"}[direction],
                    COLORS["cyan"],
                )
                for direction, position in positions.items()
            }
        else:
            for direction, position in positions.items():
                self._dpad[direction].rect = pygame.Rect(position, (button_size, button_size))

    def _move(self, direction: str) -> None:
        """Follow a corridor and react to walls, junctions, gates, and the exit."""
        if self._pending_door is not None:
            self.toast.show(
                f"Finish the challenge for door {self._pending_door} first.",
                COLORS["yellow"],
            )
            return
        result = self.engine.move_until_decision(direction)
        if result.status == "wall":
            self._shake_active = True
            self._shake_elapsed = 0.0
            self.toast.show("That path is blocked by a wall.", COLORS["yellow"])
        elif result.status == "junction":
            exits = ", ".join(self.engine.available_directions())
            self.toast.show(
                f"Junction reached. Choose a direction: {exits}.",
                COLORS["cyan"],
            )
        elif result.status == "locked_door":
            assert result.door_id is not None
            self._open_door_challenge(result.door_id)
        elif result.status == "finish":
            self._finish_run()

    def on_challenge_cancelled(self, door_id: int) -> None:
        """Clear a pending door after the learner exits an unavailable quiz."""
        if self._pending_door == door_id:
            self._pending_door = None
            self.toast.show("Challenge closed. The door is still locked.", COLORS["yellow"])

    def _open_door_challenge(self, door_id: int) -> None:
        """Open the three-question topic quiz at the selected door."""
        if self.game.state.attempts_remaining <= 0:
            self._pending_door = None
            self.game.state.completed = False
            self.game.state.completion_time = self.elapsed_seconds
            from scenes.result_scene import ResultScene

            self.game.scenes.change(ResultScene(self.game))
            return
        self._pending_door = door_id
        from scenes.challenge_scene import ChallengeScene

        challenge = ChallengeScene(
            self.game,
            door_id,
            self.on_door_unlocked,
            self.on_challenge_cancelled,
        )
        self.game.scenes.push(challenge)

    def _finish_run(self) -> None:
        """Store run completion and open the results screen when it exists."""
        self.game.state.completed = True
        self.game.state.completion_time = self.elapsed_seconds
        from scenes.result_scene import ResultScene

        self.game.scenes.change(ResultScene(self.game))


def _format_time(seconds: float) -> str:
    """Format elapsed seconds as a readable minute-and-second timer."""
    whole_seconds = max(0, int(seconds))
    minutes, remaining_seconds = divmod(whole_seconds, 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"
