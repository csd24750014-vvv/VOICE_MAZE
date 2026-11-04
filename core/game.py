"""Pygame application loop and shared services for Voice Maze."""

import pygame

import config
from core.scene_manager import Scene, SceneManager
from core.state import GameState
from scenes.menu_scene import MenuScene
from voice.commands import CommandParser
from voice.listener import VoiceListener
from voice.mic_status import MicStatus


class Game:
    """Own Pygame initialization, the main loop, and application-wide state."""

    def __init__(self) -> None:
        """Initialize the resizable window and set up the first scene."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            pygame.RESIZABLE,
        )
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.state = GameState()
        self.scenes = SceneManager(self)
        self.mic_status = MicStatus()
        self.voice_listener = VoiceListener(self.mic_status)
        self.command_parser = CommandParser()
        self.running = False
        self.scenes.change(MenuScene(self), transition=False)
        self.voice_listener.start()

    def run(self) -> None:
        """Run the non-blocking, frame-limited Pygame event loop."""
        self.running = True
        while self.running:
            delta_seconds = min(self.clock.tick(config.TARGET_FPS) / 1000.0, 0.1)
            self._process_events()
            self.scenes.update(delta_seconds)
            self.scenes.draw(self.screen)
            pygame.display.flip()
        self.shutdown()

    def _process_events(self) -> None:
        """Dispatch window events and preserve the configured minimum size."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                width = max(config.MIN_SCREEN_WIDTH, event.w)
                height = max(config.MIN_SCREEN_HEIGHT, event.h)
                self.screen = pygame.display.set_mode(
                    (width, height),
                    pygame.RESIZABLE,
                )
            else:
                self.scenes.handle_event(event)

    def shutdown(self) -> None:
        """Release Pygame resources after the main loop exits."""
        self.voice_listener.stop()
        pygame.quit()
