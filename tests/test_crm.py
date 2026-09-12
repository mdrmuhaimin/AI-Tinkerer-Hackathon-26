import sqlite3
from pathlib import Path

import pytest

from crm.db import ContactStore, StoreError
from crm.graph import build_graph
from crm.normalize import normalize_email, normalize_name, normalize_phone
from crm.state import CRMState
from tests.helpers import FakeEmbedder, FakeExtractor, FakeTranscriber

SARAH = {
    "full_name": "Sarah Khan",
    "company": "NexaTech Solutions",
    "job_title": "Product Manager",
    "email": "sarah@nexatech.example",
    "phone": "+1 555 0100",
    "website": "https://nexatech.example",
    "address": "San Francisco",
}

SARAH_NOTES = (
    "So I met this person in an event. She is a very good contact "
    "for our CRM project and would like to follow up with her after two weeks."
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


def _store(tmp_path: Path) -> ContactStore:
    return ContactStore(tmp_path / "crm.db")


def _run(
    tmp_path: Path,
    payload: dict,
    *,
    transcript: str | None = None,
    typed_notes: str | None = None,
    store: ContactStore | None = None,
    name: str | None = None,
):
    image = _touch(tmp_path / "card.jpg")
    voice = None
    transcriber = FakeTranscriber()
    if transcript is not None:
        voice = _touch(tmp_path / "note.ogg")
        transcriber = FakeTranscriber(transcript)
    active = store if store is not None else _store(tmp_path)
    graph = build_graph(
        extractor=FakeExtractor(payload),
        transcriber=transcriber,
        store=active,
        embedder=FakeEmbedder(),
    )
    result = graph.invoke(
        _pending(
            name=name or payload.get("full_name") or "Someone",
            image_path=image,
            voice_path=voice,
            typed_notes=typed_notes,
        )
    )
    return result, active


def _count(store: ContactStore) -> int:
    with sqlite3.connect(store.db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]


def test_new_contact_creates_exactly_one_row(tmp_path: Path) -> None:
    result, store = _run(tmp_path, SARAH)
    assert result["status"] == "complete"
    assert result["contact_id"] is not None
    assert result.get("crm_action") == "created"
    assert _count(store) == 1
    row = store.get(result["contact_id"])
    assert row["full_name"] == "Sarah Khan"
    assert row["company"] == "NexaTech Solutions"
    assert row["source"] == "conference_capture"
    assert row["created_at"]
    assert row["updated_at"]


def test_same_normalized_email_updates_same_id(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH)
    second, _ = _run(
        tmp_path,
        {**SARAH, "email": "  SARAH@NEXATECH.EXAMPLE  ", "job_title": "VP Product"},
        store=store,
    )
    assert second["status"] == "complete"
    assert second["contact_id"] == first["contact_id"]
    assert second.get("crm_action") == "updated"
    assert _count(store) == 1
    assert store.get(first["contact_id"])["job_title"] == "VP Product"


def test_same_normalized_phone_without_email_updates(tmp_path: Path) -> None:
    payload = {**SARAH, "email": None}
    first, store = _run(tmp_path, payload)
    second, _ = _run(
        tmp_path,
        {**payload, "phone": "+1-555-0100", "job_title": "Director"},
        store=store,
    )
    assert second["contact_id"] == first["contact_id"]
    assert _count(store) == 1
    assert store.get(first["contact_id"])["job_title"] == "Director"


def test_same_normalized_name_and_company_without_email_phone_updates(
    tmp_path: Path,
) -> None:
    payload = {**SARAH, "email": None, "phone": None}
    first, store = _run(tmp_path, payload)
    second, _ = _run(
        tmp_path,
        {
            **payload,
            "full_name": "  sarah   khan ",
            "company": "nexatech solutions",
            "job_title": "Head of Product",
        },
        store=store,
    )
    assert second["contact_id"] == first["contact_id"]
    assert _count(store) == 1
    assert store.get(first["contact_id"])["job_title"] == "Head of Product"


def test_same_name_different_emails_are_two_contacts(tmp_path: Path) -> None:
    first, store = _run(
        tmp_path,
        {**SARAH, "email": "sarah@nexatech.com"},
    )
    second, _ = _run(
        tmp_path,
        {**SARAH, "email": "sarah@other.com", "phone": "+1 555 0199"},
        store=store,
    )
    assert second["contact_id"] != first["contact_id"]
    assert _count(store) == 2
    assert store.get(first["contact_id"])["email"] == "sarah@nexatech.com"
    assert store.get(second["contact_id"])["email"] == "sarah@other.com"


def test_same_name_different_company_creates_second_row(tmp_path: Path) -> None:
    first, store = _run(tmp_path, {**SARAH, "email": None, "phone": None})
    second, _ = _run(
        tmp_path,
        {**SARAH, "email": None, "phone": None, "company": "Other Corp"},
        store=store,
    )
    assert second["contact_id"] != first["contact_id"]
    assert _count(store) == 2
    assert store.get(first["contact_id"])["company"] == "NexaTech Solutions"


def test_same_input_twice_still_one_row(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH)
    second, _ = _run(tmp_path, SARAH, store=store)
    assert second["contact_id"] == first["contact_id"]
    assert _count(store) == 1


def test_create_without_voice_notes_null_and_complete(tmp_path: Path) -> None:
    result, store = _run(tmp_path, SARAH)
    assert result["status"] == "complete"
    assert result["conversation_notes"] is None
    assert result.get("typed_notes") in (None, "")
    assert store.get(result["contact_id"])["notes"] is None


def test_typed_notes_stored_in_notes(tmp_path: Path) -> None:
    result, store = _run(tmp_path, SARAH, typed_notes="Met at AI Tinkerer.")
    assert result["status"] == "complete"
    assert result["conversation_notes"] == "Met at AI Tinkerer."
    assert store.get(result["contact_id"])["notes"] == "Met at AI Tinkerer."


def test_typed_and_voice_notes_both_stored(tmp_path: Path) -> None:
    typed = "Potential consulting opportunity."
    voice = "Met at LEAP and discussed data warehouse modernization."
    result, store = _run(tmp_path, SARAH, transcript=voice, typed_notes=typed)
    expected = f"{typed}\n\n{voice}"
    assert result["conversation_notes"] == expected
    assert store.get(result["contact_id"])["notes"] == expected


def test_later_typed_notes_append_not_replace(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH, typed_notes="First meeting notes.")
    second, _ = _run(tmp_path, SARAH, typed_notes="Follow up next week.", store=store)
    assert second["contact_id"] == first["contact_id"]
    assert _count(store) == 1
    assert store.get(first["contact_id"])["notes"] == (
        "First meeting notes.\n\nFollow up next week."
    )


def test_conversation_notes_stored_in_notes(tmp_path: Path) -> None:
    result, store = _run(tmp_path, SARAH, transcript=SARAH_NOTES)
    assert result["status"] == "complete"
    assert result["conversation_notes"] == SARAH_NOTES
    assert store.get(result["contact_id"])["notes"] == SARAH_NOTES


def test_second_run_appends_notes_and_keeps_one_row(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH, transcript="First meeting notes.")
    second, _ = _run(tmp_path, SARAH, transcript="Follow up next week.", store=store)
    assert second["contact_id"] == first["contact_id"]
    assert _count(store) == 1
    notes = store.get(first["contact_id"])["notes"]
    assert "First meeting notes." in notes
    assert "Follow up next week." in notes
    assert notes == "First meeting notes.\n\nFollow up next week."


def test_second_run_without_new_notes_leaves_notes_unchanged(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH, transcript="Keep this.")
    second, _ = _run(tmp_path, SARAH, store=store)
    assert second["contact_id"] == first["contact_id"]
    assert store.get(first["contact_id"])["notes"] == "Keep this."


def test_new_null_phone_email_does_not_erase_existing(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH)
    second, _ = _run(
        tmp_path,
        {**SARAH, "email": "sarah@nexatech.example", "phone": None, "website": None},
        store=store,
    )
    row = store.get(first["contact_id"])
    assert second["contact_id"] == first["contact_id"]
    assert row["phone"] == "+1 555 0100"
    assert row["email"] == "sarah@nexatech.example"
    assert row["website"] == "https://nexatech.example"


def test_persist_tests_never_construct_groq(
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
    result, store = _run(tmp_path, SARAH, transcript=SARAH_NOTES)
    assert result["status"] == "complete"
    assert _count(store) == 1


def test_invalid_or_error_does_not_write_db(tmp_path: Path) -> None:
    store = _store(tmp_path)
    graph = build_graph(
        extractor=FakeExtractor(SARAH),
        transcriber=FakeTranscriber(),
        store=store,
        embedder=FakeEmbedder(),
    )
    result = graph.invoke(_pending(name="Sarah Khan", image_path=None))
    assert result["status"] == "invalid"
    assert result["contact_id"] is None
    assert _count(store) == 0


def test_failed_update_does_not_fallback_to_create(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH)

    def boom(*_args, **_kwargs):
        raise StoreError("disk full")

    store.update = boom  # type: ignore[method-assign]
    second, _ = _run(tmp_path, SARAH, store=store)
    assert second["status"] == "error"
    assert second["contact_id"] is None
    assert any("disk full" in error for error in second["errors"])
    assert _count(store) == 1
    assert store.get(first["contact_id"])["full_name"] == "Sarah Khan"


def test_no_voice_stream_includes_normalize_search_create(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    graph = build_graph(
        extractor=FakeExtractor(SARAH),
        transcriber=FakeTranscriber(),
        store=_store(tmp_path),
        embedder=FakeEmbedder(),
    )
    nodes = [next(iter(chunk)) for chunk in graph.stream(
        _pending(name="Sarah Khan", image_path=image)
    )]
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


def test_normalize_email_phone_name() -> None:
    assert normalize_email("  Ada@Example.COM ") == "ada@example.com"
    assert normalize_phone("+44 20 0000 0000") == "+442000000000"
    assert normalize_phone("020 0000 0000") == "02000000000"
    assert normalize_name("  Sarah   Khan ") == "sarah khan"
    assert normalize_name("NexaTech Solutions") == "nexatech solutions"
