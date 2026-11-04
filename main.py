"""Launch the Voice Maze desktop game."""

from core.game import Game


def main() -> None:
    """Create the game and run its event loop."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
