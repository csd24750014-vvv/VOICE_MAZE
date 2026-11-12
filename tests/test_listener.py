"""Verify speech recognition is tuned for accessible, responsive commands."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import config
from voice.listener import VoiceListener, _configure_recognizer
from voice.offline import (
    OfflineEngineUnavailableError,
    OfflineSession,
    load_offline_model,
    recognize_offline,
)


class _FakeRecognizer:
    """Provide the SpeechRecognition fields touched by the tuning helper."""

    dynamic_energy_threshold: bool
    dynamic_energy_ratio: float
    dynamic_energy_adjustment_damping: float
    pause_threshold: float
    non_speaking_duration: float
    phrase_threshold: float
    operation_timeout: float


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
        self.assertEqual(
            recognizer.operation_timeout,
            config.VOICE["online_operation_timeout_seconds"],
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

        with (
            patch.dict("sys.modules", {"speech_recognition": fake_speech_recognition}),
            patch("voice.listener.load_offline_model", return_value=None),
            patch.dict(
                config.VOICE,
                {
                    "online_retry_initial_seconds": 0.0,
                    "online_retry_max_seconds": 0.0,
                },
            ),
        ):
            listener._listen_worker()

        messages = listener.drain_messages()
        self.assertEqual([message.kind for message in messages], ["error", "recognized"])
        self.assertEqual(messages[-1].text, "start")

    def test_missing_model_selects_online_fallback(self) -> None:
        """Do not require a downloaded model to keep the existing online path usable."""
        with patch("voice.offline.import_module") as import_module:
            result = load_offline_model(Path("missing-offline-model"))

        self.assertIsNone(result)
        import_module.assert_not_called()

    def test_installed_model_without_vosk_reports_online_fallback(self) -> None:
        """Use online recognition when the model exists but Vosk is not installed."""
        with TemporaryDirectory() as temporary_directory:
            model_path = Path(temporary_directory)
            model_file = model_path / "am" / "final.mdl"
            model_file.parent.mkdir()
            model_file.touch()
            missing_vosk = ModuleNotFoundError("No module named 'vosk'", name="vosk")
            with patch("voice.offline.import_module", side_effect=missing_vosk):
                with self.assertRaises(OfflineEngineUnavailableError):
                    load_offline_model(model_path)

    def test_missing_offline_engine_falls_back_to_online_recognition(self) -> None:
        """Keep the listener alive and accept commands from online speech."""
        listener = VoiceListener()

        class FakeRecognizer:
            """Recognize a phrase through the existing Google online adapter."""

            def adjust_for_ambient_noise(self, microphone: object, duration: float) -> None:
                del microphone, duration

            def listen(self, microphone: object, timeout: float, phrase_time_limit: float) -> object:
                del microphone, timeout, phrase_time_limit
                return object()

            def recognize_google(self, audio: object, language: str) -> str:
                del audio, language
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
            RequestError=type("RequestError", (Exception,), {}),
        )
        missing_engine = OfflineEngineUnavailableError("Vosk is not installed.")
        with (
            patch.dict("sys.modules", {"speech_recognition": fake_speech_recognition}),
            patch("voice.listener.load_offline_model", side_effect=missing_engine),
        ):
            listener._listen_worker()

        messages = listener.drain_messages()
        self.assertEqual(
            [(message.kind, message.text) for message in messages],
            [
                (
                    "notice",
                    "Vosk is not installed. Trying online recognition; internet is "
                    "required. Install Vosk in this Python environment to enable "
                    "offline voice.",
                ),
                ("recognized", "start"),
            ],
        )

    def test_offline_transcription_converts_audio_and_returns_vosk_text(self) -> None:
        """Convert captured audio to Vosk's PCM format and return its transcript."""
        class FakeAudio:
            """Record the sample format requested by the Vosk adapter."""

            def __init__(self) -> None:
                self.requested_format: tuple[int, int] | None = None

            def get_raw_data(self, convert_rate: int, convert_width: int) -> bytes:
                self.requested_format = (convert_rate, convert_width)
                return b"pcm"

        class FakeRecognizer:
            """Record audio accepted by the fake offline recognizer."""

            def __init__(self, result: str) -> None:
                self.result = result
                self.audio = b""
                self.reset_called = False

            def AcceptWaveform(self, data: bytes) -> bool:
                self.audio = data
                return True

            def FinalResult(self) -> str:
                return self.result

            def Reset(self) -> None:
                self.reset_called = True

        class FakeVosk:
            """Return a deterministic result through the Vosk recognizer interface."""

            def __init__(self) -> None:
                self.recognizers: list[FakeRecognizer] = []

            def KaldiRecognizer(
                self,
                model: object,
                sample_rate: int,
                grammar: str | None = None,
            ) -> FakeRecognizer:
                del model, sample_rate, grammar
                result = (
                    '{"text": "start"}'
                    if not self.recognizers
                    else '{"text": "some spoken answer"}'
                )
                recognizer = FakeRecognizer(result)
                self.recognizers.append(recognizer)
                return recognizer

        audio = FakeAudio()
        backend = FakeVosk()
        session = OfflineSession(object(), backend)
        transcript = recognize_offline(audio, session)

        self.assertEqual(transcript, "start")
        self.assertEqual(audio.requested_format, (16_000, 2))
        self.assertTrue(backend.recognizers[0].reset_called)
        self.assertFalse(backend.recognizers[1].reset_called)

    def test_offline_recognition_falls_back_to_free_form_answers(self) -> None:
        """Use unconstrained local transcription for text answers in quiz context."""
        class FakeAudio:
            """Provide captured audio in the conversion expected by Vosk."""

            def get_raw_data(self, convert_rate: int, convert_width: int) -> bytes:
                del convert_rate, convert_width
                return b"pcm"

        class FakeRecognizer:
            """Return the assigned transcript and record decoder resets."""

            def __init__(self, result: str) -> None:
                self.result = result
                self.reset_called = False

            def AcceptWaveform(self, data: bytes) -> bool:
                del data
                return True

            def FinalResult(self) -> str:
                return self.result

            def Reset(self) -> None:
                self.reset_called = True

        class FakeVosk:
            """Provide distinct command and free-form recognition outputs."""

            def __init__(self) -> None:
                self.recognizers = [
                    FakeRecognizer('{"text": "unrecognized phrase"}'),
                    FakeRecognizer('{"text": "a variable stores a value"}'),
                ]

            def KaldiRecognizer(
                self,
                model: object,
                sample_rate: int,
                grammar: str | None = None,
            ) -> FakeRecognizer:
                del model, sample_rate, grammar
                return self.recognizers.pop(0)

        backend = FakeVosk()
        command_recognizer, free_recognizer = backend.recognizers
        session = OfflineSession(object(), backend)
        transcript = recognize_offline(FakeAudio(), session, context="answer")

        self.assertEqual(transcript, "a variable stores a value")
        self.assertTrue(command_recognizer.reset_called)
        self.assertTrue(free_recognizer.reset_called)

    def test_listener_uses_online_recognition_when_available(self) -> None:
        """Prefer online recognition while the service is responding."""
        listener = VoiceListener()

        class FakeRecognizer:
            """Recognize the first phrase online while the local model is available."""

            def adjust_for_ambient_noise(self, microphone: object, duration: float) -> None:
                del microphone, duration

            def listen(self, microphone: object, timeout: float, phrase_time_limit: float) -> object:
                del microphone, timeout, phrase_time_limit
                return object()

            def recognize_google(self, audio: object, language: str) -> str:
                del audio, language
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
            RequestError=type("RequestError", (Exception,), {}),
        )

        with (
            patch.dict("sys.modules", {"speech_recognition": fake_speech_recognition}),
            patch("voice.listener.load_offline_model", return_value=(object(), object())),
            patch("voice.listener.OfflineSession", return_value=object()),
            patch("voice.listener.recognize_offline") as offline_recognition,
        ):
            listener._listen_worker()

        messages = listener.drain_messages()
        self.assertEqual(
            [(message.kind, message.text) for message in messages],
            [("recognized", "start")],
        )
        offline_recognition.assert_not_called()
        self.assertEqual(listener.status.state, "idle")

    def test_slow_online_recognition_falls_back_offline_for_same_phrase(self) -> None:
        """Use Vosk immediately when an online recognition request times out."""
        listener = VoiceListener()

        class FakeRequestError(Exception):
            """Represent a slow or unavailable online speech service."""

        class FakeRecognizer:
            """Fail online recognition once so the same audio uses the local model."""

            def adjust_for_ambient_noise(self, microphone: object, duration: float) -> None:
                del microphone, duration

            def listen(self, microphone: object, timeout: float, phrase_time_limit: float) -> object:
                del microphone, timeout, phrase_time_limit
                return object()

            def recognize_google(self, audio: object, language: str) -> str:
                del audio, language
                raise FakeRequestError

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

        def fake_offline_recognition(
            audio: object,
            session: OfflineSession,
            context: str | None = None,
        ) -> str:
            del audio, session, context
            listener._stop_event.set()
            return "start"

        with (
            patch.dict("sys.modules", {"speech_recognition": fake_speech_recognition}),
            patch("voice.listener.load_offline_model", return_value=(object(), object())),
            patch("voice.listener.OfflineSession", return_value=object()),
            patch("voice.listener.recognize_offline", side_effect=fake_offline_recognition),
        ):
            listener._listen_worker()

        messages = listener.drain_messages()
        self.assertEqual(
            [message.kind for message in messages],
            ["notice", "recognized"],
        )
        self.assertIn("Switched to offline voice", messages[0].text)
        self.assertEqual(messages[1].text, "start")
        self.assertEqual(listener.status.state, "idle")


if __name__ == "__main__":
    unittest.main()
