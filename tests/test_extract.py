from pathlib import Path

from crm.graph import build_graph
from crm.providers.base import ExtractorError
from crm.schemas import ContactEvidence
from crm.state import CRMState
from tests.helpers import FakeEmbedder, FakeExtractor

FULL_PAYLOAD = {
    "full_name": "Ada Lovelace",
    "company": "Analytical Engines",
    "job_title": "Mathematician",
    "email": "ada@example.com",
    "phone": "+44 20 0000 0000",
    "website": "https://ada.example",
    "address": "London",
}


def _pending(
    *,
    name: str | None,
    image_path: str | None,
    voice_path: str | None = None,
) -> CRMState:
    return {
        "name": name,
        "image_path": image_path,
        "voice_path": voice_path,
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


def _graph(tmp_path: Path, extractor: FakeExtractor):
    return build_graph(
        extractor=extractor, db_path=tmp_path / "crm.db", embedder=FakeEmbedder()
    )


def test_fake_full_payload_matches_contact_evidence(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    fake = FakeExtractor(FULL_PAYLOAD)
    result = _graph(tmp_path, fake).invoke(
        _pending(name="Ada Lovelace", image_path=image)
    )

    expected = ContactEvidence.model_validate(FULL_PAYLOAD).model_dump()
    assert result["status"] == "complete"
    assert result["errors"] == []
    assert result["contact_evidence"] == expected
    assert fake.calls == [image]


def test_fake_only_full_name_does_not_invent_fields(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")

    omitted = _graph(tmp_path, FakeExtractor({"full_name": "Ada Lovelace"})).invoke(
        _pending(name="Ada Lovelace", image_path=image)
    )
    assert omitted["status"] == "complete"
    evidence = omitted["contact_evidence"]
    assert evidence["full_name"] == "Ada Lovelace"
    assert evidence["company"] is None
    assert evidence["job_title"] is None
    assert evidence["email"] is None
    assert evidence["phone"] is None
    assert evidence["website"] is None
    assert evidence["address"] is None

    explicit_nulls = {
        "full_name": "Ada Lovelace",
        "company": None,
        "job_title": None,
        "email": None,
        "phone": None,
        "website": None,
        "address": None,
    }
    nulled = _graph(tmp_path, FakeExtractor(explicit_nulls)).invoke(
        _pending(name="Ada Lovelace", image_path=image)
    )
    assert nulled["status"] == "complete"
    assert nulled["contact_evidence"]["full_name"] == "Ada Lovelace"
    assert nulled["contact_evidence"]["company"] is None
    assert nulled["contact_evidence"]["email"] is None


def test_fake_invalid_payload_is_schema_invalid(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")

    missing_name = _graph(tmp_path, FakeExtractor({"company": "Analytical Engines"})).invoke(
        _pending(name="Ada Lovelace", image_path=image)
    )
    assert missing_name["status"] == "invalid"
    assert missing_name["contact_evidence"] is None
    assert missing_name["errors"]
    assert any("schema" in error.lower() for error in missing_name["errors"])

    wrong_types = _graph(tmp_path, FakeExtractor({"full_name": 123})).invoke(
        _pending(name="Ada Lovelace", image_path=image)
    )
    assert wrong_types["status"] == "invalid"
    assert wrong_types["contact_evidence"] is None
    assert wrong_types["errors"]
    assert any("schema" in error.lower() for error in wrong_types["errors"])


def test_fake_extractor_error_sets_error_status(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    fake = FakeExtractor(error=ExtractorError("provider unavailable"))
    result = _graph(tmp_path, fake).invoke(
        _pending(name="Ada Lovelace", image_path=image)
    )

    assert result["status"] == "error"
    assert result["contact_evidence"] is None
    assert result["errors"]
    assert any("provider unavailable" in error for error in result["errors"])
    assert any("extract" in error.lower() for error in result["errors"])
    assert fake.calls == [image]


def test_invalid_input_does_not_call_extractor(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    fake = FakeExtractor(FULL_PAYLOAD)
    result = _graph(tmp_path, fake).invoke(
        _pending(name=None, image_path=image)
    )

    assert result["status"] == "invalid"
    assert result["contact_evidence"] is None
    assert fake.calls == []
