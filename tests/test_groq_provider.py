from pathlib import Path

import pytest

from crm.providers.base import ExtractorError, TranscriberError
from crm.providers.groq import GroqCardExtractor, GroqVoiceTranscriber


def test_from_env_requires_groq_api_key(monkeypatch) -> None:
    monkeypatch.setattr("crm.providers.groq.load_dotenv", lambda: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ExtractorError, match="GROQ_API_KEY"):
        GroqCardExtractor.from_env()

    with pytest.raises(TranscriberError, match="GROQ_API_KEY"):
        GroqVoiceTranscriber.from_env()


def test_from_env_reads_groq_api_key(monkeypatch) -> None:
    monkeypatch.setattr("crm.providers.groq.load_dotenv", lambda: None)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    extractor = GroqCardExtractor.from_env()
    assert extractor._api_key == "test-key"

    transcriber = GroqVoiceTranscriber.from_env()
    assert transcriber._api_key == "test-key"


def test_transcribe_uses_whisper_large_v3_and_wraps_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}
    voice = tmp_path / "note.ogg"
    voice.write_bytes(b"ogg")

    class _Result:
        text = "hello from whisper"

    class _Transcriptions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Result()

    class _Audio:
        transcriptions = _Transcriptions()

    class _Client:
        def __init__(self, **_kwargs):
            self.audio = _Audio()

    monkeypatch.setattr("crm.providers.groq.Groq", _Client)
    transcriber = GroqVoiceTranscriber(api_key="test-key")
    assert transcriber.transcribe(str(voice)) == "hello from whisper"
    assert captured["model"] == "whisper-large-v3"
    assert captured["file"] is not None

    class _Boom:
        def __init__(self, **_kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr("crm.providers.groq.Groq", _Boom)
    with pytest.raises(TranscriberError, match="network down"):
        GroqVoiceTranscriber(api_key="test-key").transcribe(str(voice))
