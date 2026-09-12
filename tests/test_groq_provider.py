from pathlib import Path

import pytest

from crm.providers.base import ExtractorError, TranscriberError
from crm.providers.groq import GroqCardExtractor, GroqSearchAnswerer, GroqVoiceTranscriber


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


def test_search_answer_hides_reasoning_and_strips_legacy_think_block(monkeypatch) -> None:
    captured: dict = {}

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = type("Message", (), {
                "content": "<think>private reasoning</think>\nYou met Mariana Anderson."
            })()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class _Client:
        def __init__(self, **_kwargs):
            self.chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr("crm.providers.groq.Groq", _Client)

    answer = GroqSearchAnswerer(api_key="test-key").answer("Who?", [])

    assert captured["reasoning_format"] == "hidden"
    assert answer == "You met Mariana Anderson."


@pytest.mark.parametrize("content", [
    "<think>private reasoning</think>",
    "<think>unfinished reasoning",
    "orphaned reasoning</think>",
    "<think>reason</think>\nYou met <think>Mariana</think>.",
    None,
    "   ",
])
def test_search_answer_rejects_reasoning_without_safe_final_text(
    content: str | None, monkeypatch
) -> None:
    class _Completions:
        def create(self, **_kwargs):
            message = type("Message", (), {"content": content})()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class _Client:
        def __init__(self, **_kwargs):
            self.chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr("crm.providers.groq.Groq", _Client)

    with pytest.raises(ValueError, match="empty search answer"):
        GroqSearchAnswerer(api_key="test-key").answer("Who?", [])


def test_search_answer_preserves_plain_final_text(monkeypatch) -> None:
    class _Completions:
        def create(self, **_kwargs):
            message = type("Message", (), {"content": "  You met Mariana Anderson.  "})()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class _Client:
        def __init__(self, **_kwargs):
            self.chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr("crm.providers.groq.Groq", _Client)

    assert GroqSearchAnswerer(api_key="test-key").answer("Who?", []) == (
        "You met Mariana Anderson."
    )
