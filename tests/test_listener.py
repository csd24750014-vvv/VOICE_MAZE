"""Verify speech recognition is tuned for accessible, responsive commands."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
from voice.listener import VoiceListener, _configure_recognizer


class _FakeRecognizer:
    """Provide the SpeechRecognition fields touched by the tuning helper."""

    dynamic_energy_threshold: bool
    dynamic_energy_ratio: float
    dynamic_energy_adjustment_damping: float
    pause_threshold: float
    non_speaking_duration: float
    phrase_threshold: float


class ListenerConfigurationTests(unittest.TestCase):
    """Check recognizer sensitivity and phrase timing without hardware."""

    def test_recognizer_uses_adaptive_sensitivity_and_short_pause_settings(self) -> None:
        """The listener adapts to room noise and submits short phrases promptly."""
        recognizer = _FakeRecognizer()

        _configure_recognizer(recognizer)

        self.assertTrue(recognizer.dynamic_energy_threshold)
        self.assertEqual(
            recognizer.dynamic_energy_ratio,
            config.VOICE["dynamic_energy_ratio"],
        )
        self.assertEqual(
            recognizer.dynamic_energy_adjustment_damping,
            config.VOICE["dynamic_energy_adjustment_damping"],
        )
        self.assertEqual(
            recognizer.pause_threshold,
            config.VOICE["pause_threshold_seconds"],
        )
        self.assertEqual(
            recognizer.non_speaking_duration,
            config.VOICE["non_speaking_duration_seconds"],
        )
        self.assertEqual(
            recognizer.phrase_threshold,
            config.VOICE["phrase_threshold_seconds"],
        )
        self.assertLess(recognizer.pause_threshold, 0.8)
        self.assertLessEqual(
            recognizer.non_speaking_duration,
            recognizer.pause_threshold,
        )

    def test_listener_recovers_after_temporary_google_recognition_failure(self) -> None:
        """Keep accepting voice phrases after a transient online service failure."""
        listener = VoiceListener()

        class FakeRequestError(Exception):
            """Represent a temporary Google recognition outage."""

        class FakeRecognizer:
            """Return one service error followed by a successfully recognized phrase."""

            def __init__(self) -> None:
                self.calls = 0

            def adjust_for_ambient_noise(self, microphone: object, duration: float) -> None:
                del microphone, duration

            def listen(self, microphone: object, timeout: float, phrase_time_limit: float) -> object:
                del microphone, timeout, phrase_time_limit
                return object()

            def recognize_google(self, audio: object, language: str) -> str:
                del audio, language
                self.calls += 1
                if self.calls == 1:
                    raise FakeRequestError
                listener._stop_event.set()
                return "start"

        class FakeMicrophone:
            """Provide the context-manager interface expected by SpeechRecognition."""

            def __enter__(self) -> "FakeMicrophone":
                return self

            def __exit__(self, *args: object) -> None:
                del args

        fake_speech_recognition = SimpleNamespace(
            Recognizer=FakeRecognizer,
            Microphone=FakeMicrophone,
            WaitTimeoutError=type("WaitTimeoutError", (Exception,), {}),
            UnknownValueError=type("UnknownValueError", (Exception,), {}),
            RequestError=FakeRequestError,
        )

        with patch.dict("sys.modules", {"speech_recognition": fake_speech_recognition}):
            listener._listen_worker()

        messages = listener.drain_messages()
        self.assertEqual([message.kind for message in messages], ["error", "recognized"])
        self.assertEqual(messages[-1].text, "start")


if __name__ == "__main__":
    unittest.main()
