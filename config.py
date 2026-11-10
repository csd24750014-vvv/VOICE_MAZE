"""Shared settings for the Voice Maze game."""

from pathlib import Path

# Keep paths relative to this file so the project works from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
SCORES_FILE = DATA_DIR / "scores.json"
ASSETS_DIR = PROJECT_ROOT / "assets"

# The game starts large enough to show its learning and maze panels comfortably.
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 810
MIN_SCREEN_WIDTH = 1280
MIN_SCREEN_HEIGHT = 720
WINDOW_TITLE = "Voice Maze"
TARGET_FPS = 60

# The debug switch is intentionally off; normal play never depends on a keyboard.
DEBUG_KEYBOARD_ENABLED = False

# Reusable palette used by both the game and its reusable UI components.
COLORS = {
    "background": (12, 15, 29),
    "surface": (22, 27, 47),
    "surface_light": (31, 38, 63),
    "surface_highlight": (42, 51, 82),
    "text": (239, 244, 255),
    "text_muted": (156, 169, 197),
    "cyan": (66, 232, 246),
    "cyan_dark": (28, 155, 181),
    "purple": (173, 116, 255),
    "pink": (255, 105, 180),
    "green": (75, 231, 163),
    "yellow": (255, 207, 89),
    "red": (255, 93, 112),
    "border": (57, 69, 105),
    "black": (4, 6, 14),
}

# Font names use installed system fonts and safely fall back through Pygame.
FONTS = {
    "body": "segoeui",
    "heading": "segoeuisemibold",
    "mono": "consolas",
}

# Animation and interaction timings are in seconds unless noted otherwise.
TIMINGS = {
    "transition_seconds": 0.24,
    "toast_seconds": 2.8,
    "command_cooldown_seconds": 0.35,
    "particle_lifetime_seconds": 3.2,
}

# Speech is captured in short windows so the microphone worker can stop promptly.
VOICE = {
    "language": "en-US",
    "listen_timeout_seconds": 0.8,
    "phrase_limit_seconds": 4,
    "ambient_calibration_seconds": 0.4,
    "dynamic_energy_ratio": 1.25,
    "dynamic_energy_adjustment_damping": 0.1,
    "pause_threshold_seconds": 0.38,
    "non_speaking_duration_seconds": 0.24,
    "phrase_threshold_seconds": 0.15,
    "fuzzy_match_threshold": 0.78,
}
