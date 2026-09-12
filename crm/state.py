from typing import Literal, TypedDict


class CRMState(TypedDict):
    name: str | None
    image_path: str | None
    voice_path: str | None
    status: Literal[
        "pending",
        "loaded",
        "valid",
        "invalid",
        "extracted",
        "error",
        "complete",
    ]
    errors: list[str]
    contact_evidence: dict | None
    extracted_card: dict | None
    voice_transcript: str | None
    conversation_notes: str | None
    normalized_contact: dict | None
    matched_contact_id: int | None
    contact_id: int | None
    crm_action: str | None
    verified_contact: dict | None
    search_document: str | None
    embedding: list[float] | None
