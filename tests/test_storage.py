from crm.storage import SQLiteContactStore


def result(name, notes=None):
    return {
        "status": "complete", "errors": [],
        "contact_evidence": {
            "full_name": name, "company": "Acme", "job_title": None,
            "email": None, "phone": None, "website": None, "address": None,
        },
        "voice_transcript": notes, "conversation_notes": notes,
    }


def test_schema_save_round_trip_fts_and_owner_isolation(tmp_path):
    store = SQLiteContactStore(tmp_path / "contacts.sqlite3")
    store.save(1, result("Ada", "Met at LEAP in Riyadh"))
    store.save(2, result("Grace", "Met at LEAP in Riyadh"))

    found = store.search(1, "who did I meet at LEAP?", 5)

    assert len(found) == 1
    assert found[0]["full_name"] == "Ada"
    assert found[0]["conversation_notes"] == "Met at LEAP in Riyadh"
    assert store.search(3, "LEAP") == []
    assert store.search(1, '" OR * NOT (') == []


def test_search_is_limited_to_five(tmp_path):
    store = SQLiteContactStore(tmp_path / "contacts.sqlite3")
    for index in range(7):
        store.save(1, result(f"Person {index}", "Tinkerer conference"))
    assert len(store.search(1, "Tinkerer", 99)) == 5
