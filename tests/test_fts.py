import sqlite3

from crm.db import ContactStore
from crm.graph import build_graph
from tests.helpers import FakeExtractor, FakeTranscriber


def fields(name, notes):
    return {
        "full_name": name,
        "company": "Acme",
        "job_title": None,
        "email": None,
        "phone": None,
        "website": None,
        "address": None,
        "notes": notes,
    }


def test_create_update_query_safety_and_limit(tmp_path):
    store = ContactStore(tmp_path / "crm.db")
    contact_id = store.create(fields("Ada", "Met at LEAP"))
    assert store.search("who did I meet at LEAP?")[0]["full_name"] == "Ada"

    store.update(contact_id, fields("Ada", "Discussed robotics"))
    assert store.search("robotics")[0]["id"] == contact_id
    assert store.search('" OR * NOT (') == []

    for index in range(7):
        store.create(fields(f"Person {index}", "Tinkerer conference"))
    assert len(store.search("Tinkerer", limit=99)) == 5


def test_existing_contacts_are_backfilled(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, "
            "company TEXT, job_title TEXT, email TEXT, phone TEXT, website TEXT, address TEXT, "
            "notes TEXT, source TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.execute("INSERT INTO contacts(full_name, notes) VALUES (?, ?)", ("Grace", "Met in Dhaka"))

    store = ContactStore(path)
    assert store.search("Dhaka")[0]["full_name"] == "Grace"


def test_default_capture_never_constructs_groq_embedder(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "crm.graph.GroqEmbedder.from_env",
        classmethod(lambda cls: (_ for _ in ()).throw(AssertionError("unsupported endpoint"))),
    )
    image = tmp_path / "card.jpg"
    image.write_bytes(b"card")
    store = ContactStore(tmp_path / "crm.db")
    graph = build_graph(
        extractor=FakeExtractor(fields("Ada", None) | {"notes": None}),
        transcriber=FakeTranscriber(),
        store=store,
    )
    state = {
        "name": None, "image_path": str(image), "voice_path": None,
        "status": "pending", "errors": [],
    }
    nodes = [next(iter(chunk)) for chunk in graph.stream(state)]
    result = graph.invoke(state)
    assert result["status"] == "complete"
    assert "create_embedding" not in nodes
    assert "store_embedding" not in nodes
    assert store.get_embedding(result["contact_id"]) is None
