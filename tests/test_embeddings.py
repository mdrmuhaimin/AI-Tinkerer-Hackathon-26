import sqlite3
from pathlib import Path

import pytest

from crm.db import ContactStore, StoreError
from crm.graph import build_graph
from crm.providers.base import EmbedderError
from crm.search import build_search_document, query_contacts
from tests.helpers import FakeEmbedder, FakeExtractor, FakeTranscriber
from tests.test_crm import SARAH, _pending, _run, _store, _touch

WORKFLOW_NOTES = (
    "Met Sarah at an event. She is interested in AI workflow automation "
    "for product teams and a possible CRM pilot."
)
DECOY = {
    "full_name": "Bob Mariner",
    "company": "Harbor Sails",
    "job_title": "Captain",
    "email": "bob@harbor.example",
    "phone": "+1 555 0199",
    "website": None,
    "address": None,
}
DECOY_NOTES = "We talked about sailing, cheese tasting, and weekend golf."
RELATED_QUERY = "Who did I meet regarding AI workflow automation?"

CONTACTS_COLUMNS = {
    "id",
    "full_name",
    "company",
    "job_title",
    "email",
    "phone",
    "website",
    "address",
    "notes",
    "source",
    "created_at",
    "updated_at",
}


def _graph(
    tmp_path: Path,
    *,
    payload: dict | None = None,
    transcript: str | None = None,
    store: ContactStore | None = None,
    embedder: FakeEmbedder | None = None,
    extractor: FakeExtractor | None = None,
):
    return build_graph(
        extractor=extractor or FakeExtractor(payload or SARAH),
        transcriber=FakeTranscriber(transcript or ""),
        store=store or _store(tmp_path),
        embedder=embedder or FakeEmbedder(),
    )


def test_successful_create_writes_embedding_row(tmp_path: Path) -> None:
    result, store = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES)
    assert result["status"] == "complete"
    assert store.get_embedding(result["contact_id"]) is not None


def test_query_returns_related_contact_not_decoy(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES)
    second, _ = _run(tmp_path, DECOY, transcript=DECOY_NOTES, store=store)
    assert first["contact_id"] != second["contact_id"]

    embedder = FakeEmbedder()
    hits = query_contacts(store, embedder, RELATED_QUERY, limit=5)
    assert hits
    assert hits[0]["full_name"] == "Sarah Khan"
    assert hits[0]["id"] == first["contact_id"]
    assert "distance" in hits[0]
    assert RELATED_QUERY not in (store.get(first["contact_id"])["notes"] or "")


def test_related_phrasing_ranks_above_decoy(tmp_path: Path) -> None:
    _, store = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES)
    _run(tmp_path, DECOY, transcript=DECOY_NOTES, store=store)
    hits = query_contacts(store, FakeEmbedder(), RELATED_QUERY)
    names = [h["full_name"] for h in hits]
    assert names[0] == "Sarah Khan"
    if "Bob Mariner" in names:
        assert names.index("Sarah Khan") < names.index("Bob Mariner")


def test_notes_update_refreshes_embedding(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH, transcript="First meeting notes.")
    before = store.get_embedding(first["contact_id"])
    assert before is not None
    second, _ = _run(
        tmp_path, SARAH, transcript="Follow up about workflow automation.", store=store
    )
    after = store.get_embedding(second["contact_id"])
    assert after is not None
    assert after != before
    assert second["status"] == "complete"


def test_contacts_table_has_no_embedding_column(tmp_path: Path) -> None:
    result, store = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES)
    assert result["status"] == "complete"
    with sqlite3.connect(store.db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(contacts)")}
    assert cols == CONTACTS_COLUMNS
    assert "embedding" not in cols


def test_failed_verify_skips_embedding(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.get = lambda _cid: None  # type: ignore[method-assign]
    result, _ = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES, store=store)
    assert result["status"] == "error"
    assert result.get("verified_contact") is None
    raw = ContactStore(store.db_path)
    assert raw.get_embedding(result["contact_id"]) is None


def test_embed_error_is_not_complete(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "note.ogg")
    store = _store(tmp_path)
    graph = _graph(
        tmp_path,
        transcript=WORKFLOW_NOTES,
        store=store,
        embedder=FakeEmbedder(error=EmbedderError("embed down")),
    )
    result = graph.invoke(
        _pending(name="Sarah Khan", image_path=image, voice_path=voice)
    )
    assert result["status"] == "error"
    assert result["status"] != "complete"
    assert any("embed" in e.lower() for e in result["errors"])
    assert store.get_embedding(result["contact_id"]) is None


def test_store_embedding_error_is_not_complete(tmp_path: Path) -> None:
    store = _store(tmp_path)

    def boom(*_args, **_kwargs):
        raise StoreError("vec write failed")

    store.upsert_embedding = boom  # type: ignore[method-assign]
    result, _ = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES, store=store)
    assert result["status"] == "error"
    assert result["status"] != "complete"
    assert any("vec write failed" in e for e in result["errors"])


def test_default_suite_does_not_construct_live_embedder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("live embedder constructed")

    monkeypatch.setattr("crm.providers.embeddings.GroqEmbedder.from_env", boom)
    monkeypatch.setattr("crm.graph.GroqEmbedder.from_env", classmethod(lambda cls: boom()))
    result, store = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES)
    assert result["status"] == "complete"
    assert store.get_embedding(result["contact_id"]) is not None


def test_build_search_document_joins_only_allowed_fields() -> None:
    doc = build_search_document(
        {
            "full_name": "Sarah Khan",
            "company": "NexaTech",
            "job_title": "PM",
            "notes": "workflow",
            "email": "hidden@example.com",
            "phone": "555",
            "website": "https://nope.example",
            "address": "nowhere",
        }
    )
    assert doc == "Sarah Khan NexaTech PM workflow"
    assert "hidden@example.com" not in doc
    assert "555" not in doc
    assert "https://nope.example" not in doc
    assert "nowhere" not in doc
