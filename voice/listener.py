"""Non-blocking speech recognition worker with a queue for game scenes."""

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Lock, Thread
import time
from typing import Literal, Optional, Protocol

import config
from voice.mic_status import MicStateName, MicStatus
from voice.offline import (
    OfflineEngineUnavailableError,
    OfflineSession,
    load_offline_model,
    recognize_offline,
)

VoiceMessageKind = Literal["recognized", "unrecognized", "notice", "error"]
_MIC_STATES: dict[tuple[str, str], MicStateName] = {
    ("processing", "offline"): "processing_offline",
    ("processing", "online"): "processing_online",
    ("listening", "offline"): "listening_offline",
    ("listening", "online"): "listening_online",
}


class _ConfigurableRecognizer(Protocol):
    """SpeechRecognition settings required by the voice capture loop."""

    dynamic_energy_threshold: bool
    dynamic_energy_ratio: float
    dynamic_energy_adjustment_damping: float
    operation_timeout: float
    pause_threshold: float
    non_speaking_duration: float
    phrase_threshold: float


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
        self._context_lock = Lock()
        self._command_context: Optional[str] = None
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

    def set_command_context(self, context: Optional[str]) -> None:
        """Publish the active scene's parser context to the voice worker."""
        with self._context_lock:
            self._command_context = context

    def _get_command_context(self) -> Optional[str]:
        """Read the active scene context without racing the game thread."""
        with self._context_lock:
            return self._command_context

    def _listen_worker(self) -> None:
        """Own microphone access, recognition, and recoverable error handling."""
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            _configure_recognizer(recognizer)
            try:
                offline_setup = load_offline_model(config.VOICE["offline_model_dir"])
            except OfflineEngineUnavailableError as error:
                offline_setup = None
                self.messages.put(
                    VoiceMessage(
                        "notice",
                        f"{error} Trying online recognition; internet is required. "
                        "Install Vosk in this Python environment to enable offline voice.",
                    )
                )
            except (ImportError, OSError, RuntimeError, ValueError):
                offline_setup = None
                self.messages.put(
                    VoiceMessage(
                        "notice",
                        "Offline voice is unavailable. Trying online recognition; "
                        "internet is required for voice input.",
                    )
                )
            offline_session: Optional[OfflineSession] = None
            if offline_setup is not None:
                try:
                    offline_session = OfflineSession(
                        offline_setup[0],
                        offline_setup[1],
                    )
                except (ImportError, OSError, RuntimeError, ValueError):
                    offline_setup = None
                    offline_session = None
                    self.messages.put(
                        VoiceMessage(
                            "notice",
                            "Offline voice setup failed. Trying online recognition; "
                            "internet is required for voice input.",
                        )
                    )
            recognition_mode: Literal["offline", "online"] = "online"
            online_retry_at = 0.0
            online_retry_delay = config.VOICE["online_retry_initial_seconds"]
            online_unavailable_reported = False
            offline_switch_reported = False
            last_unrecognized_at = float("-inf")
            with sr.Microphone() as microphone:
                self.status.set(
                    _MIC_STATES[("processing", "online")],
                    "Calibrating microphone noise for online voice recognition.",
                )
                recognizer.adjust_for_ambient_noise(
                    microphone,
                    duration=config.VOICE["ambient_calibration_seconds"],
                )
                while not self._stop_event.is_set():
                    if recognition_mode == "offline" and time.monotonic() >= online_retry_at:
                        recognition_mode = "online"
                    online_backoff = (
                        offline_session is None
                        and online_retry_at > time.monotonic()
                    )
                    if online_backoff:
                        self.status.set(
                            "online_unavailable",
                            "Online speech is unavailable; checking the connection again.",
                        )
                    else:
                        self.status.set(
                            _MIC_STATES[("listening", recognition_mode)],
                            (
                                "Listening; online recognition is being retried."
                                if recognition_mode == "online" and offline_switch_reported
                                else f"Listening for a voice command ({recognition_mode})."
                            ),
                        )
                    try:
                        audio = recognizer.listen(
                            microphone,
                            timeout=config.VOICE["listen_timeout_seconds"],
                            phrase_time_limit=config.VOICE["phrase_limit_seconds"],
                        )
                    except sr.WaitTimeoutError:
                        continue
                    if online_backoff:
                        continue

                    heard_phrase = ""
                    tried_online = recognition_mode == "online"
                    self.status.set(
                        _MIC_STATES[("processing", recognition_mode)],
                        f"Recognizing your speech ({recognition_mode}).",
                    )
                    if tried_online:
                        try:
                            heard_phrase = recognizer.recognize_google(
                                audio,
                                language=self.language,
                            ).strip()
                        except sr.RequestError:
                            online_retry_at = time.monotonic() + online_retry_delay
                            online_retry_delay = min(
                                config.VOICE["online_retry_max_seconds"],
                                online_retry_delay * 2,
                            )
                            if offline_session is None:
                                self.status.set(
                                    "listening_online",
                                    "Online recognition is unavailable. Check your internet connection.",
                                )
                                if not online_unavailable_reported:
                                    self.messages.put(
                                        VoiceMessage(
                                            "error",
                                            "Online speech recognition is unavailable. "
                                            "Check your internet connection. Mouse controls "
                                            "remain available.",
                                        )
                                    )
                                    online_unavailable_reported = True
                                continue
                            recognition_mode = "offline"
                            if not offline_switch_reported:
                                self.messages.put(
                                    VoiceMessage(
                                        "notice",
                                        "Internet is slow or unavailable. Switched to "
                                        "offline voice; commands will keep working.",
                                    )
                                )
                                offline_switch_reported = True
                            try:
                                heard_phrase = recognize_offline(
                                    audio,
                                    offline_session,
                                    context=self._get_command_context(),
                                )
                            except (OSError, RuntimeError, ValueError):
                                self.status.set(
                                    "error",
                                    "Online recognition failed and offline recognition "
                                    "could not process this phrase. Please try again.",
                                )
                                self.messages.put(
                                    VoiceMessage(
                                        "error",
                                        "Both voice recognition methods had trouble with "
                                        "that phrase. Try again or use the mouse.",
                                    )
                                )
                                continue
                        except sr.UnknownValueError:
                            if offline_session is None:
                                heard_phrase = ""
                            else:
                                try:
                                    heard_phrase = recognize_offline(
                                        audio,
                                        offline_session,
                                        context=self._get_command_context(),
                                    )
                                except (OSError, RuntimeError, ValueError):
                                    heard_phrase = ""
                    else:
                        if offline_session is None:
                            recognition_mode = "online"
                            continue
                        try:
                            phrase = recognize_offline(
                                audio,
                                offline_session,
                                context=self._get_command_context(),
                            )
                            heard_phrase = phrase
                        except (OSError, RuntimeError, ValueError):
                            self.messages.put(
                                VoiceMessage(
                                    "notice",
                                    "Offline recognition needs attention. Retrying "
                                    "online voice now.",
                                )
                            )
                            offline_session = None
                            offline_setup = None
                            recognition_mode = "online"
                            try:
                                heard_phrase = recognizer.recognize_google(
                                    audio,
                                    language=self.language,
                                ).strip()
                            except sr.RequestError:
                                online_retry_at = time.monotonic() + online_retry_delay
                                online_retry_delay = min(
                                    config.VOICE["online_retry_max_seconds"],
                                    online_retry_delay * 2,
                                )
                                if not online_unavailable_reported:
                                    self.messages.put(
                                        VoiceMessage(
                                            "error",
                                            "Online speech recognition is unavailable. "
                                            "Check your internet connection; mouse controls "
                                            "remain available.",
                                        )
                                    )
                                    online_unavailable_reported = True
                                continue
                            except sr.UnknownValueError:
                                heard_phrase = ""

                    if tried_online and heard_phrase and recognition_mode == "online":
                        online_retry_delay = config.VOICE["online_retry_initial_seconds"]
                        online_retry_at = 0.0
                        if offline_switch_reported:
                            self.messages.put(
                                VoiceMessage(
                                    "notice",
                                    "Internet recognition is available again.",
                                )
                            )
                        offline_switch_reported = False
                        online_unavailable_reported = False

                    if heard_phrase:
                        last_unrecognized_at = float("-inf")
                        self.messages.put(VoiceMessage("recognized", heard_phrase))
                    elif time.monotonic() - last_unrecognized_at >= config.VOICE[
                        "unrecognized_feedback_cooldown_seconds"
                    ]:
                        self.messages.put(
                            VoiceMessage(
                                "unrecognized",
                                "No clear words were recognized. Speak after the "
                                "listening indicator appears, or use the mouse.",
                            )
                        )
                        last_unrecognized_at = time.monotonic()
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


def _configure_recognizer(recognizer: _ConfigurableRecognizer) -> None:
    """Tune sensitivity, command pauses, and the maximum network wait."""
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_ratio = config.VOICE["dynamic_energy_ratio"]
    recognizer.dynamic_energy_adjustment_damping = config.VOICE[
        "dynamic_energy_adjustment_damping"
    ]
    recognizer.pause_threshold = config.VOICE["pause_threshold_seconds"]
    recognizer.non_speaking_duration = config.VOICE["non_speaking_duration_seconds"]
    recognizer.phrase_threshold = config.VOICE["phrase_threshold_seconds"]
    recognizer.operation_timeout = config.VOICE[
        "online_operation_timeout_seconds"
    ]
