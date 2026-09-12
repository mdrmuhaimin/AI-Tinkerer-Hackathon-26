from pathlib import Path

from crm.db import ContactStore, StoreError
from crm.graph import build_graph
from tests.helpers import FakeEmbedder, FakeExtractor, FakeTranscriber
from tests.test_crm import SARAH, _pending, _run, _store, _touch


def test_successful_write_verifies(tmp_path: Path) -> None:
    result, store = _run(tmp_path, SARAH)
    assert result["status"] == "complete"
    assert result["verified_contact"]["id"] == result["contact_id"]
    row = store.get(result["contact_id"])
    assert result["verified_contact"]["email"] == row["email"]
    assert result["verified_contact"]["full_name"] == row["full_name"]
    assert row["email"]
    assert row["full_name"]


def test_missing_record_fails(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.get = lambda _cid: None  # type: ignore[method-assign]
    result, _ = _run(tmp_path, SARAH, store=store)
    assert result["status"] == "error"
    assert result["status"] != "complete"
    assert any("verification failed: contact not found" in e for e in result["errors"])
    assert result.get("verified_contact") is None


def test_incorrect_stored_values_fail(tmp_path: Path) -> None:
    store = _store(tmp_path)
    real_get = ContactStore.get

    def wrong(cid):
        row = real_get(store, cid)
        if row is None:
            return None
        return {**row, "email": "wrong@example.com"}

    store.get = wrong  # type: ignore[method-assign]
    result, _ = _run(tmp_path, SARAH, store=store)
    assert result["status"] == "error"
    assert result["status"] != "complete"
    assert any("email" in e for e in result["errors"])
    assert result.get("verified_contact") is None


def test_database_exception_on_get_is_error(tmp_path: Path) -> None:
    store = _store(tmp_path)

    def boom(_cid):
        raise StoreError("locked")

    store.get = boom  # type: ignore[method-assign]
    result, _ = _run(tmp_path, SARAH, store=store)
    assert result["status"] == "error"
    assert result["status"] != "complete"
    assert any("verification failed:" in e for e in result["errors"])
    assert result.get("verified_contact") is None


def test_final_success_contains_stored_contact_id(tmp_path: Path) -> None:
    result, store = _run(tmp_path, SARAH)
    assert result["status"] == "complete"
    assert result["contact_id"] is not None
    assert result["verified_contact"]["id"] == result["contact_id"]
    assert result["contact_id"] == store.get(result["contact_id"])["id"]


def test_successful_run_verified_contact_matches_store_get(tmp_path: Path) -> None:
    first, store = _run(tmp_path, SARAH)
    assert first["status"] == "complete"
    assert first["verified_contact"] == store.get(first["contact_id"])
    second, _ = _run(
        tmp_path,
        {**SARAH, "job_title": "VP Product"},
        store=store,
    )
    assert second["status"] == "complete"
    assert second["verified_contact"] == store.get(second["contact_id"])


def test_create_stream_includes_verify_write(tmp_path: Path) -> None:
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


def test_update_stream_includes_verify_write(tmp_path: Path) -> None:
    _, store = _run(tmp_path, SARAH)
    image = _touch(tmp_path / "card2.jpg")
    graph = build_graph(
        extractor=FakeExtractor(SARAH),
        transcriber=FakeTranscriber(),
        store=store,
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
        "update_contact",
        "verify_write",
        "build_search_document",
        "create_embedding",
        "store_embedding",
        "finalize",
    ]
