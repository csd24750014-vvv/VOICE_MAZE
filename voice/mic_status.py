"""Thread-safe microphone state shared by the listener and game interface."""

from dataclasses import dataclass
from threading import Lock
from typing import Literal

MicStateName = Literal[
    "idle",
    "listening",
    "processing",
    "listening_offline",
    "processing_offline",
    "listening_online",
    "processing_online",
    "online_unavailable",
    "error",
]


@dataclass(frozen=True)
class MicSnapshot:
    """Immutable view of the current microphone state."""

    state: MicStateName
    message: str


class MicStatus:
    """Protect current microphone state from concurrent thread access."""

    def __init__(self) -> None:
        """Start in idle state before the voice worker is launched."""
        self._lock = Lock()
        self._snapshot = MicSnapshot("idle", "Voice input is ready.")

    def set(self, state: MicStateName, message: str) -> None:
        """Publish a new microphone state and its user-facing explanation."""
        with self._lock:
            self._snapshot = MicSnapshot(state, message)

    def snapshot(self) -> MicSnapshot:
        """Return a consistent copy of the current microphone state."""
        with self._lock:
            return self._snapshot

    @property
    def state(self) -> MicStateName:
        """Return the current state label."""
        return self.snapshot().state

    @property
    def message(self) -> str:
        """Return the current status text for on-screen display."""
        return self.snapshot().message
