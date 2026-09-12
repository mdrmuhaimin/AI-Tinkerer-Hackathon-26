import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from crm.graph import build_graph
from crm.schemas import ContactEvidence

pytestmark = pytest.mark.live

CARD_IMAGE = Path(__file__).resolve().parents[1] / "input" / "visiting_card.png"


def test_live_extract_visiting_card() -> None:
    load_dotenv()
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY must be set in the environment or .env")

    result = build_graph().invoke(
        {
            "name": "live",
            "image_path": str(CARD_IMAGE),
            "voice_path": None,
            "status": "pending",
            "errors": [],
            "contact_evidence": None,
            "extracted_card": None,
        }
    )

    assert result["status"] == "complete"
    evidence = ContactEvidence.model_validate(result["contact_evidence"])
    assert evidence.full_name.strip()
