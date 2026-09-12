import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from crm.graph import build_graph
from crm.schemas import ContactEvidence
from tests.helpers import FakeExtractor

pytestmark = pytest.mark.live

CARD_IMAGE = Path(__file__).resolve().parents[1] / "input" / "visiting_card.png"
VOICE_NOTE = (
    Path(__file__).resolve().parents[1] / "input" / "6134386456120009929.ogg"
)


def test_live_transcribe_voice_note() -> None:
    load_dotenv()
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY must be set in the environment or .env")
    if not VOICE_NOTE.is_file():
        pytest.skip("input/6134386456120009929.ogg is not present")
    if not CARD_IMAGE.is_file():
        pytest.skip("input/visiting_card.png is not present")

    result = build_graph(extractor=FakeExtractor({"full_name": "Sarah Khan"})).invoke(
        {
            "name": "Sarah Khan",
            "image_path": str(CARD_IMAGE),
            "voice_path": str(VOICE_NOTE),
            "status": "pending",
            "errors": [],
            "contact_evidence": None,
            "extracted_card": None,
            "voice_transcript": None,
            "conversation_notes": None,
        }
    )

    assert result["status"] == "complete"
    evidence = ContactEvidence.model_validate(result["contact_evidence"])
    assert evidence.full_name.strip()
    assert result["voice_transcript"]
    assert result["conversation_notes"] == result["voice_transcript"]
