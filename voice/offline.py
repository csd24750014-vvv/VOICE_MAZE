"""Adapters for local Vosk speech recognition."""

import json
from importlib import import_module
from pathlib import Path
from typing import Optional, Protocol, cast

from voice.commands import offline_command_phrases, parse_command


class AudioData(Protocol):
    """Expose the SpeechRecognition audio conversion needed by Vosk."""

    def get_raw_data(self, convert_rate: int, convert_width: int) -> bytes:
        """Return audio samples converted to the requested PCM format."""


class OfflineRecognizer(Protocol):
    """Describe the Vosk recognizer operations used for one captured phrase."""

    def AcceptWaveform(self, data: bytes) -> bool:
        """Accept PCM samples and report whether a complete result is ready."""

    def FinalResult(self) -> str:
        """Return the final recognition result as JSON."""

    def Reset(self) -> None:
        """Reset decoder state after completing one phrase."""


class VoskBackend(Protocol):
    """Describe the small public Vosk API used by this application."""

    def Model(self, model_path: str) -> object:
        """Load the speech model stored at the supplied directory."""

    def KaldiRecognizer(
        self,
        model: object,
        sample_rate: int,
        grammar: str | None = None,
    ) -> OfflineRecognizer:
        """Create a recognizer for audio captured at the supplied rate."""


class OfflineEngineUnavailableError(RuntimeError):
    """Explain that the active Python environment lacks the Vosk runtime."""


class OfflineSession:
    """Keep command-biased and free-form decoders warm between voice phrases."""

    def __init__(self, model: object, backend: VoskBackend) -> None:
        """Build persistent decoders for command matching and spoken answers."""
        command_phrases = set(offline_command_phrases())
        command_phrases.add("[unk]")
        command_grammar = json.dumps(sorted(command_phrases))
        self.command_recognizer = backend.KaldiRecognizer(
            model,
            16_000,
            command_grammar,
        )
        self.free_recognizer = backend.KaldiRecognizer(model, 16_000)

    def transcribe(
        self,
        pcm_data: bytes,
        context: Optional[str] = None,
    ) -> str:
        """Prefer a recognized game command, otherwise keep free-form speech."""
        command_text = _decode_and_reset(self.command_recognizer, pcm_data)
        if command_text:
            command = parse_command(command_text, context=context)
            if command is not None and (
                context != "answer"
                or command.action in {"option", "back", "return_to_maze"}
            ):
                return command_text
        return _decode_and_reset(self.free_recognizer, pcm_data)


def load_offline_model(model_path: Path) -> tuple[object, VoskBackend] | None:
    """Load a configured model, requiring Vosk if the model directory exists."""
    if not (model_path / "am" / "final.mdl").is_file():
        return None
    try:
        backend = cast(VoskBackend, import_module("vosk"))
    except ImportError as error:
        raise OfflineEngineUnavailableError(
            "The offline model is present but the Vosk engine or one of its "
            "dependencies is not installed in this Python environment."
        ) from error
    return backend.Model(str(model_path)), backend


def recognize_offline(
    audio: AudioData,
    session: OfflineSession,
    context: Optional[str] = None,
) -> str:
    """Transcribe locally, preferring game commands without losing answer text."""
    pcm_data = audio.get_raw_data(convert_rate=16_000, convert_width=2)
    return session.transcribe(pcm_data, context=context)


def _decode_and_reset(recognizer: OfflineRecognizer, pcm_data: bytes) -> str:
    """Decode a single PCM phrase and reset its persistent recognizer."""
    try:
        recognizer.AcceptWaveform(pcm_data)
        result = json.loads(recognizer.FinalResult())
    finally:
        recognizer.Reset()
    if not isinstance(result, dict) or not isinstance(result.get("text"), str):
        raise ValueError("Offline speech recognition returned an invalid result.")
    return result["text"].strip()
