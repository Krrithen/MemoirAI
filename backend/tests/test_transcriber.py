"""FasterWhisperTranscriber error classification, without downloading a model."""

import io
import wave
from types import SimpleNamespace

import pytest

from app.providers.transcriber import FasterWhisperTranscriber, TranscriptionFailed


def silent_wav(seconds: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * int(16000 * seconds))
    return buf.getvalue()


def transcriber_with_model(model) -> FasterWhisperTranscriber:
    t = FasterWhisperTranscriber("tiny", "int8")
    t.__dict__["_model"] = model  # skip the real (downloaded) model
    return t


class StubModel:
    def __init__(self, segments=None, error=None):
        self.segments, self.error = segments or [], error

    def transcribe(self, samples, vad_filter):
        if self.error:
            raise self.error
        return iter(self.segments), None


def test_undecodable_audio_is_permanent_and_never_loads_the_model():
    t = FasterWhisperTranscriber("tiny", "int8")
    with pytest.raises(TranscriptionFailed, match="Couldn't decode"):
        t.transcribe(b"this is not audio" * 20, ".webm")
    assert "_model" not in t.__dict__


def test_model_errors_are_not_permanent():
    t = transcriber_with_model(StubModel(error=MemoryError("out of memory")))
    with pytest.raises(MemoryError):
        t.transcribe(silent_wav(), ".wav")


def test_silence_is_no_speech():
    with pytest.raises(TranscriptionFailed, match="No speech"):
        transcriber_with_model(StubModel()).transcribe(silent_wav(), ".wav")


def test_speech_is_joined_into_text():
    segments = [SimpleNamespace(text=" Hello"), SimpleNamespace(text=" world. ")]
    assert transcriber_with_model(StubModel(segments)).transcribe(silent_wav(), ".wav") == "Hello world."
