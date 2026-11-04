"""Non-blocking speech recognition worker with a queue for game scenes."""

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread
from typing import Literal, Optional

import config
from voice.mic_status import MicStatus

VoiceMessageKind = Literal["recognized", "unrecognized", "error"]


@dataclass(frozen=True)
class VoiceMessage:
    """One speech result or recoverable voice-input error for the main thread."""

    kind: VoiceMessageKind
    text: str


class VoiceListener:
    """Capture and recognize microphone input without blocking the game loop."""

    def __init__(
        self,
        status: Optional[MicStatus] = None,
        language: str = config.VOICE["language"],
    ) -> None:
        """Prepare the result queue and worker controls without opening audio."""
        self.status = status or MicStatus()
        self.language = language
        self.messages: Queue[VoiceMessage] = Queue()
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    @property
    def is_running(self) -> bool:
        """Report whether the background recognition thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start listening in a daemon thread; repeated starts are harmless."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = Thread(
            target=self._listen_worker,
            name="VoiceMazeSpeechListener",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Request shutdown and briefly join the worker without blocking long."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(0.0, timeout))
        if not self.is_running:
            self.status.set("idle", "Voice input is paused.")

    def get_message(self) -> Optional[VoiceMessage]:
        """Return the oldest pending speech result without waiting."""
        try:
            return self.messages.get_nowait()
        except Empty:
            return None

    def drain_messages(self) -> list[VoiceMessage]:
        """Return all currently queued results without blocking."""
        result: list[VoiceMessage] = []
        while True:
            message = self.get_message()
            if message is None:
                return result
            result.append(message)

    def _listen_worker(self) -> None:
        """Own microphone access, recognition, and recoverable error handling."""
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            with sr.Microphone() as microphone:
                self.status.set("processing", "Calibrating microphone noise.")
                recognizer.adjust_for_ambient_noise(
                    microphone,
                    duration=config.VOICE["ambient_calibration_seconds"],
                )
                while not self._stop_event.is_set():
                    self.status.set("listening", "Listening for a voice command.")
                    try:
                        audio = recognizer.listen(
                            microphone,
                            timeout=config.VOICE["listen_timeout_seconds"],
                            phrase_time_limit=config.VOICE["phrase_limit_seconds"],
                        )
                    except sr.WaitTimeoutError:
                        continue

                    self.status.set("processing", "Recognizing your speech.")
                    try:
                        phrase = recognizer.recognize_google(
                            audio,
                            language=self.language,
                        ).strip()
                    except sr.UnknownValueError:
                        self.messages.put(
                            VoiceMessage(
                                "unrecognized",
                                "I couldn't hear that clearly. Say that again.",
                            )
                        )
                        continue
                    except sr.RequestError:
                        message = (
                            "Online speech recognition is unavailable. "
                            "Use the mouse to keep playing."
                        )
                        self.status.set("error", message)
                        self.messages.put(VoiceMessage("error", message))
                        break

                    if phrase:
                        self.messages.put(VoiceMessage("recognized", phrase))
                if self._stop_event.is_set():
                    self.status.set("idle", "Voice input is paused.")
        except ImportError:
            message = (
                "SpeechRecognition or PyAudio is not installed. "
                "Use the mouse to keep playing."
            )
            self.status.set("error", message)
            self.messages.put(VoiceMessage("error", message))
        except (AttributeError, OSError, RuntimeError, ValueError):
            message = (
                "Microphone unavailable. Check your microphone and permissions, "
                "or use the mouse to keep playing."
            )
            self.status.set("error", message)
            self.messages.put(VoiceMessage("error", message))
