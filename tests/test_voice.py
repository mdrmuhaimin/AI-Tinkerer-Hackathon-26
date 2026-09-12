from pathlib import Path

import pytest

from crm.graph import build_graph, merge_context
from crm.providers.base import ExtractorError, TranscriberError
from crm.schemas import ContactEvidence
from crm.state import CRMState
from tests.helpers import FakeEmbedder, FakeExtractor, FakeTranscriber

FULL_PAYLOAD = {
    "full_name": "Sarah Khan",
    "company": "Acme Robotics",
    "job_title": "Product Lead",
    "email": "sarah@example.com",
    "phone": "+1 555 0100",
    "website": "https://acme.example",
    "address": "Austin",
}

FAKE_TRANSCRIPT = (
    "Met Sarah at AI Tinkerer Hackathon.\n"
    "She is interested in AI workflow automation for product teams.\n"
    "We discussed a possible pilot.\n"
    "Follow up next week and send her the demo."
)


def _pending(
    *,
    name: str | None,
    image_path: str | None,
    voice_path: str | None = None,
    typed_notes: str | None = None,
) -> CRMState:
    return {
        "name": name,
        "image_path": image_path,
        "voice_path": voice_path,
        "typed_notes": typed_notes,
        "status": "pending",
        "errors": [],
        "contact_evidence": None,
        "extracted_card": None,
        "voice_transcript": None,
        "conversation_notes": None,
    }


def _touch(path: Path) -> str:
    path.write_bytes(b"placeholder")
    return str(path)


def _graph(
    tmp_path: Path,
    extractor: FakeExtractor | None = None,
    transcriber: FakeTranscriber | None = None,
):
    if extractor is None:
        extractor = FakeExtractor(FULL_PAYLOAD)
    if transcriber is None:
        transcriber = FakeTranscriber(FAKE_TRANSCRIPT)
    return build_graph(
        extractor=extractor,
        transcriber=transcriber,
        db_path=tmp_path / "crm.db",
        embedder=FakeEmbedder(),
    )


def _stream_node_names(graph, state: CRMState) -> list[str]:
    return [next(iter(chunk)) for chunk in graph.stream(state)]


def test_merge_context_typed_and_voice_rules() -> None:
    base = {"status": "valid", "typed_notes": None, "voice_transcript": None}
    assert merge_context(base)["conversation_notes"] is None
    assert merge_context({**base, "typed_notes": "   "})["conversation_notes"] is None
    assert merge_context({**base, "typed_notes": "hello"})["conversation_notes"] == "hello"
    assert merge_context({**base, "voice_transcript": "voice"})["conversation_notes"] == "voice"
    assert (
        merge_context({**base, "typed_notes": "hello", "voice_transcript": "voice"})[
            "conversation_notes"
        ]
        == "hello\n\nvoice"
    )
    assert (
        merge_context({**base, "typed_notes": "  ", "voice_transcript": "voice"})[
            "conversation_notes"
        ]
        == "voice"
    )


def test_typed_notes_only_does_not_call_transcriber(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    transcriber = FakeTranscriber(FAKE_TRANSCRIPT)
    graph = _graph(tmp_path, transcriber=transcriber)
    state = _pending(
        name="Sarah Khan",
        image_path=image,
        typed_notes="Potential consulting opportunity.",
    )
    nodes = _stream_node_names(graph, state)
    result = graph.invoke(state)
    assert "transcribe_voice" not in nodes
    assert transcriber.calls == []
    assert result["status"] == "complete"
    assert result["voice_transcript"] is None
    assert result["conversation_notes"] == "Potential consulting opportunity."


def test_typed_and_voice_both_in_conversation_notes(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "sarah_note.ogg")
    typed = "Potential consulting opportunity."
    transcriber = FakeTranscriber(FAKE_TRANSCRIPT)
    result = _graph(tmp_path, transcriber=transcriber).invoke(
        _pending(
            name="Sarah Khan",
            image_path=image,
            voice_path=voice,
            typed_notes=typed,
        )
    )
    assert transcriber.calls == [voice]
    assert result["voice_transcript"] == FAKE_TRANSCRIPT
    assert result["conversation_notes"] == f"{typed}\n\n{FAKE_TRANSCRIPT}"


def test_name_and_image_without_voice_completes(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    transcriber = FakeTranscriber(FAKE_TRANSCRIPT)
    result = _graph(tmp_path, transcriber=transcriber).invoke(
        _pending(name="Sarah Khan", image_path=image)
    )

    assert result["status"] == "complete"
    assert result["errors"] == []
    assert result["contact_evidence"]["full_name"] == "Sarah Khan"
    assert result["voice_transcript"] is None
    assert result["conversation_notes"] is None
    assert transcriber.calls == []


def test_no_voice_skips_transcribe_node_and_leaves_transcript_none(
    tmp_path: Path,
) -> None:
    image = _touch(tmp_path / "card.jpg")
    transcriber = FakeTranscriber(FAKE_TRANSCRIPT)
    graph = _graph(tmp_path, transcriber=transcriber)
    state = _pending(name="Sarah Khan", image_path=image)

    nodes = _stream_node_names(graph, state)
    assert "transcribe_voice" not in nodes
    assert nodes == [
        "load_input",
        "validate_input",
        "extract_card",
        "validate_extraction",
        "merge_context",
        "normalize_contact",
        "search_crm",
        "create_contact",
        "verify_write",
        "build_search_document",
        "create_embedding",
        "store_embedding",
        "finalize",
    ]

    result = graph.invoke(state)
    assert transcriber.calls == []
    assert result["voice_transcript"] is None
    assert result["conversation_notes"] is None
    assert result["status"] == "complete"


def test_voice_file_transcribes_and_sets_conversation_notes(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "sarah_note.ogg")
    transcriber = FakeTranscriber(FAKE_TRANSCRIPT)
    graph = _graph(tmp_path, transcriber=transcriber)
    state = _pending(name="Sarah Khan", image_path=image, voice_path=voice)

    events = list(graph.stream(state))
    nodes = [next(iter(chunk)) for chunk in events]
    assert nodes == [
        "load_input",
        "validate_input",
        "extract_card",
        "validate_extraction",
        "transcribe_voice",
        "merge_context",
        "normalize_contact",
        "search_crm",
        "create_contact",
        "verify_write",
        "build_search_document",
        "create_embedding",
        "store_embedding",
        "finalize",
    ]
    assert transcriber.calls == [voice]

    result = events[-1]["finalize"]
    assert result["status"] == "complete"
    assert result["voice_transcript"] == FAKE_TRANSCRIPT
    assert result["conversation_notes"] == FAKE_TRANSCRIPT


def test_voice_does_not_overwrite_contact_evidence(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "sarah_note.ogg")
    extractor = FakeExtractor(FULL_PAYLOAD)
    transcriber = FakeTranscriber(FAKE_TRANSCRIPT)
    result = _graph(tmp_path, extractor=extractor, transcriber=transcriber).invoke(
        _pending(name="Sarah Khan", image_path=image, voice_path=voice)
    )

    expected = ContactEvidence.model_validate(FULL_PAYLOAD).model_dump()
    assert result["contact_evidence"] == expected
    assert result["contact_evidence"]["company"] == "Acme Robotics"
    assert result["voice_transcript"] == FAKE_TRANSCRIPT


def test_transcriber_error_only_when_voice_supplied(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "sarah_note.ogg")

    failing = FakeTranscriber(error=TranscriberError("stt unavailable"))
    with_voice = _graph(tmp_path, transcriber=failing).invoke(
        _pending(name="Sarah Khan", image_path=image, voice_path=voice)
    )
    assert with_voice["status"] == "error"
    assert with_voice["errors"]
    assert any("stt unavailable" in error for error in with_voice["errors"])
    assert failing.calls == [voice]
    assert with_voice["conversation_notes"] is None

    unused = FakeTranscriber(error=TranscriberError("stt unavailable"))
    without_voice = _graph(tmp_path, transcriber=unused).invoke(
        _pending(name="Sarah Khan", image_path=image)
    )
    assert without_voice["status"] == "complete"
    assert unused.calls == []
    assert without_voice["voice_transcript"] is None


def test_prior_failure_does_not_call_transcriber(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "sarah_note.ogg")
    transcriber = FakeTranscriber(FAKE_TRANSCRIPT)

    invalid = _graph(tmp_path, transcriber=transcriber).invoke(
        _pending(name=None, image_path=image, voice_path=voice)
    )
    assert invalid["status"] == "invalid"
    assert transcriber.calls == []

    extract_fail = FakeExtractor(error=ExtractorError("provider unavailable"))
    unused = FakeTranscriber(FAKE_TRANSCRIPT)
    errored = _graph(tmp_path, extractor=extract_fail, transcriber=unused).invoke(
        _pending(name="Sarah Khan", image_path=image, voice_path=voice)
    )
    assert errored["status"] == "error"
    assert unused.calls == []


def test_default_suite_does_not_construct_live_groq(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("live Groq client constructed")

    monkeypatch.setattr("crm.providers.groq.Groq", boom)
    monkeypatch.setattr(
        "crm.graph.GroqCardExtractor.from_env",
        classmethod(lambda cls: boom()),
    )
    monkeypatch.setattr(
        "crm.graph.GroqVoiceTranscriber.from_env",
        classmethod(lambda cls: boom()),
    )
    monkeypatch.setattr(
        "crm.graph.GroqEmbedder.from_env",
        classmethod(lambda cls: boom()),
    )

    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "sarah_note.ogg")
    result = _graph(tmp_path).invoke(
        _pending(name="Sarah Khan", image_path=image, voice_path=voice)
    )
    assert result["status"] == "complete"
