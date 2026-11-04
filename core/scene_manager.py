"""Scene base class and stack manager for moving through game screens."""

from typing import TYPE_CHECKING, List, Optional

import pygame

if TYPE_CHECKING:
    from core.game import Game


class Scene:
    """Base interface implemented by each full-screen game scene."""

    def __init__(self, game: "Game") -> None:
        """Keep a reference to shared game services and state."""
        self.game = game

    def enter(self) -> None:
        """Run one-time setup after this scene becomes active."""

    def exit(self) -> None:
        """Release scene-specific resources before another scene replaces it."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle one Pygame event delivered by the game loop."""

    def update(self, delta_seconds: float) -> None:
        """Advance scene animations and logic by the elapsed frame time."""

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the current scene to the supplied game surface."""


class SceneManager:
    """Maintain the active scene stack and fade between scene changes."""

    def __init__(self, game: "Game") -> None:
        """Create an empty scene stack with transitions disabled."""
        self.game = game
        self._stack: List[Scene] = []
        self._fade_alpha = 0
        self._transition_seconds = 0.0

    @property
    def current(self) -> Optional[Scene]:
        """Return the top scene, or ``None`` if the stack is empty."""
        return self._stack[-1] if self._stack else None

    def change(self, scene: Scene, transition: bool = True) -> None:
        """Replace the current scene and optionally fade in the new screen."""
        if self.current is not None:
            self.current.exit()
            self._stack.pop()
        self._stack.append(scene)
        scene.enter()
        if transition:
            self._fade_alpha = 210
            self._transition_seconds = 0.24
        else:
            self._fade_alpha = 0
            self._transition_seconds = 0.0

    def clear_and_change(self, scene: Scene, transition: bool = True) -> None:
        """Close every stacked scene before opening a fresh top-level screen."""
        while self._stack:
            self._stack.pop().exit()
        self.change(scene, transition=transition)

    def push(self, scene: Scene) -> None:
        """Place a temporary scene above the current scene."""
        if self.current is not None:
            self.current.exit()
        self._stack.append(scene)
        scene.enter()

    def pop(self) -> None:
        """Remove the top scene and resume the one underneath it."""
        if not self._stack:
            return
        self._stack.pop().exit()
        if self.current is not None:
            self.current.enter()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Send an event to the top scene when one is active."""
        if self.current is not None:
            self.current.handle_event(event)

    def update(self, delta_seconds: float) -> None:
        """Update the active scene and fade overlay without blocking."""
        if self.current is not None:
            self.current.update(delta_seconds)
        if self._fade_alpha > 0 and self._transition_seconds > 0:
            self._transition_seconds = max(0.0, self._transition_seconds - delta_seconds)
            self._fade_alpha = int(210 * self._transition_seconds / 0.24)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the active scene followed by its transition overlay."""
        if self.current is not None:
            self.current.draw(surface)
        if self._fade_alpha > 0:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((4, 6, 14, self._fade_alpha))
            surface.blit(overlay, (0, 0))
