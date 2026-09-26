import logging
import os
import tempfile
from functools import cached_property
from typing import Protocol

logger = logging.getLogger(__name__)


class TranscriptionFailed(Exception):
    """Raised when audio can't be turned into text. Never swallowed into ''."""


class Transcriber(Protocol):
    def transcribe(self, audio: bytes, suffix: str) -> str: ...


def _with_temp_file(audio: bytes, suffix: str, fn):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio)
        path = f.name
    try:
        return fn(path)
    finally:
        os.remove(path)


def _require_text(text: str | None) -> str:
    text = (text or "").strip()
    if not text:
        raise TranscriptionFailed("No speech found in the recording")
    return text


class FasterWhisperTranscriber:
    """Local transcription. The model downloads on first use, then runs offline."""

    def __init__(self, model_size: str, compute_type: str):
        self.model_size = model_size
        self.compute_type = compute_type

    @cached_property
    def _model(self):
        from faster_whisper import WhisperModel

        logger.info("Loading faster-whisper model %s (%s)", self.model_size, self.compute_type)
        return WhisperModel(self.model_size, device="cpu", compute_type=self.compute_type)

    def transcribe(self, audio: bytes, suffix: str) -> str:
        def run(path: str) -> str:
            segments, _info = self._model.transcribe(path, vad_filter=True)
            return " ".join(s.text.strip() for s in segments)

        try:
            text = _with_temp_file(audio, suffix, run)
        except Exception as e:
            raise TranscriptionFailed(f"faster-whisper failed: {e}") from e
        return _require_text(text)


class AssemblyAITranscriber:
    """Hosted transcription, opt-in with TRANSCRIBER=assemblyai."""

    def __init__(self, api_key: str):
        import assemblyai as aai

        aai.settings.api_key = api_key
        self._aai = aai

    def transcribe(self, audio: bytes, suffix: str) -> str:
        try:
            transcript = _with_temp_file(audio, suffix, self._aai.Transcriber().transcribe)
        except Exception as e:
            raise TranscriptionFailed(f"AssemblyAI failed: {e}") from e
        if transcript.status == self._aai.TranscriptStatus.error:
            raise TranscriptionFailed(f"AssemblyAI failed: {transcript.error}")
        return _require_text(transcript.text)
