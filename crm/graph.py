from pathlib import Path

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from crm.db import DEFAULT_DB_PATH, ContactStore, StoreError
from crm.normalize import normalize_evidence
from crm.providers.base import (
    CardExtractor,
    EmbedderError,
    EmbeddingProvider,
    ExtractorError,
    TranscriberError,
    VoiceTranscriber,
)
from crm.providers.embeddings import GroqEmbedder
from crm.providers.groq import GroqCardExtractor, GroqVoiceTranscriber
from crm.schemas import ContactEvidence
from crm.search import build_search_document as _search_document
from crm.state import CRMState

_DISPLAY = (
    "full_name",
    "company",
    "job_title",
    "email",
    "phone",
    "website",
    "address",
)


def _blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


def load_input(state: CRMState) -> CRMState:
    return {
        "name": state.get("name"),
        "image_path": state.get("image_path"),
        "voice_path": state.get("voice_path"),
        "typed_notes": state.get("typed_notes"),
        "status": "loaded",
        "errors": [],
        "contact_evidence": None,
        "extracted_card": None,
        "voice_transcript": None,
        "conversation_notes": None,
        "normalized_contact": None,
        "matched_contact_id": None,
        "contact_id": None,
        "crm_action": None,
        "verified_contact": None,
        "search_document": None,
        "embedding": None,
    }


def validate_input(state: CRMState) -> CRMState:
    errors: list[str] = []

    if _blank(state.get("name")):
        errors.append("name is required")

    image_path = state.get("image_path")
    if _blank(image_path):
        errors.append("image path is required")
    elif not Path(image_path).is_file():
        errors.append(f"image file not found: {image_path}")

    voice_path = state.get("voice_path")
    if not _blank(voice_path) and not Path(voice_path).is_file():
        errors.append(f"voice file not found: {voice_path}")

    if errors:
        return {**state, "status": "invalid", "errors": errors}
    return {**state, "status": "valid", "errors": []}


def extract_card(state: CRMState, extractor: CardExtractor | None) -> CRMState:
    if state.get("status") != "valid":
        return state
    try:
        active = (
            extractor
            if extractor is not None
            else GroqCardExtractor.from_env()
        )
        raw = active.extract_card(state["image_path"])
        return {**state, "status": "extracted", "extracted_card": raw}
    except ExtractorError as exc:
        return {
            **state,
            "status": "error",
            "errors": [f"card extraction failed: {exc}"],
        }
    except Exception as exc:
        return {
            **state,
            "status": "error",
            "errors": [f"card extraction failed: {exc}"],
        }


def validate_extraction(state: CRMState) -> CRMState:
    status = state.get("status")
    if status in ("invalid", "error"):
        return state
    if status != "extracted":
        return state
    try:
        evidence = ContactEvidence.model_validate(state.get("extracted_card"))
        return {
            **state,
            "status": "valid",
            "contact_evidence": evidence.model_dump(),
            "errors": [],
        }
    except ValidationError as exc:
        return {
            **state,
            "status": "invalid",
            "contact_evidence": None,
            "errors": [f"schema validation failed: {exc}"],
        }


def voice_present(state: CRMState) -> str:
    if state.get("status") in ("invalid", "error"):
        return "merge_context"
    if _blank(state.get("voice_path")):
        return "merge_context"
    if state.get("status") == "valid":
        return "transcribe_voice"
    return "merge_context"


def transcribe_voice(state: CRMState, transcriber: VoiceTranscriber | None) -> CRMState:
    try:
        active = (
            transcriber
            if transcriber is not None
            else GroqVoiceTranscriber.from_env()
        )
        text = active.transcribe(state["voice_path"])
        return {**state, "voice_transcript": text}
    except TranscriberError as exc:
        return {
            **state,
            "status": "error",
            "errors": [f"voice transcription failed: {exc}"],
        }
    except Exception as exc:
        return {
            **state,
            "status": "error",
            "errors": [f"voice transcription failed: {exc}"],
        }


def merge_context(state: CRMState) -> CRMState:
    typed = state.get("typed_notes")
    transcript = state.get("voice_transcript")
    has_typed = isinstance(typed, str) and typed.strip()
    has_voice = isinstance(transcript, str) and transcript.strip()
    if has_typed and has_voice:
        notes = f"{typed}\n\n{transcript}"
    elif has_typed:
        notes = typed
    elif has_voice:
        notes = transcript
    else:
        notes = None
    return {**state, "conversation_notes": notes}


def persistable(state: CRMState) -> str:
    if state.get("status") in ("invalid", "error"):
        return "finalize"
    return "normalize_contact"


def normalize_contact(state: CRMState) -> CRMState:
    if state.get("status") != "valid" or not state.get("contact_evidence"):
        return state
    return {**state, "normalized_contact": normalize_evidence(state["contact_evidence"])}


def search_crm(state: CRMState, store: ContactStore) -> CRMState:
    if state.get("status") != "valid" or not state.get("normalized_contact"):
        return state
    try:
        return {**state, "matched_contact_id": store.find_match(state["normalized_contact"])}
    except StoreError as exc:
        return {**state, "status": "error", "errors": [f"crm search failed: {exc}"]}
    except Exception as exc:
        return {**state, "status": "error", "errors": [f"crm search failed: {exc}"]}


def match_found(state: CRMState) -> str:
    if state.get("status") in ("invalid", "error"):
        return "finalize"
    if state.get("matched_contact_id") is not None:
        return "update_contact"
    if state.get("status") == "valid" and state.get("contact_evidence"):
        return "create_contact"
    return "finalize"


def _display_fields(state: CRMState) -> dict:
    normalized = state.get("normalized_contact") or {}
    fields = {key: normalized.get(key) for key in _DISPLAY}
    fields["notes"] = state.get("conversation_notes")
    return fields


def create_contact(state: CRMState, store: ContactStore) -> CRMState:
    try:
        contact_id = store.create(_display_fields(state))
        return {**state, "contact_id": contact_id, "crm_action": "created"}
    except StoreError as exc:
        return {**state, "status": "error", "errors": [f"crm create failed: {exc}"]}
    except Exception as exc:
        return {**state, "status": "error", "errors": [f"crm create failed: {exc}"]}


def update_contact(state: CRMState, store: ContactStore) -> CRMState:
    try:
        store.update(state["matched_contact_id"], _display_fields(state))
        return {
            **state,
            "contact_id": state["matched_contact_id"],
            "crm_action": "updated",
        }
    except StoreError as exc:
        return {**state, "status": "error", "errors": [f"crm update failed: {exc}"]}
    except Exception as exc:
        return {**state, "status": "error", "errors": [f"crm update failed: {exc}"]}


def _json_row(row: dict) -> dict:
    return {
        k: v if isinstance(v, (str, int, float, bool, type(None))) else str(v)
        for k, v in row.items()
    }


def verify_write(state: CRMState, store: ContactStore) -> CRMState:
    if state.get("status") in ("invalid", "error"):
        return state
    contact_id = state.get("contact_id")
    if contact_id is None:
        return {
            **state,
            "status": "error",
            "errors": ["verification failed: missing contact id"],
        }
    try:
        row = store.get(contact_id)
    except StoreError as exc:
        return {**state, "status": "error", "errors": [f"verification failed: {exc}"]}
    except Exception as exc:
        return {**state, "status": "error", "errors": [f"verification failed: {exc}"]}
    if row is None:
        return {
            **state,
            "status": "error",
            "errors": ["verification failed: contact not found"],
        }
    mismatches = []
    intended = state.get("normalized_contact") or {}
    for key in _DISPLAY:
        want = intended.get(key)
        if _blank(want):
            continue
        if row.get(key) != want:
            mismatches.append(key)
    notes = state.get("conversation_notes")
    if notes and notes not in (row.get("notes") or ""):
        mismatches.append("notes")
    if mismatches:
        return {
            **state,
            "status": "error",
            "errors": [f"verification failed: {', '.join(mismatches)}"],
        }
    return {**state, "verified_contact": _json_row(row)}


def write_ok(state: CRMState) -> str:
    if state.get("status") == "valid" and state.get("verified_contact") is not None:
        return "write_ok"
    return "write_failed"


def build_search_document(state: CRMState) -> CRMState:
    return {
        **state,
        "search_document": _search_document(state["verified_contact"]),
    }


def create_embedding(
    state: CRMState, embedder: EmbeddingProvider | None
) -> CRMState:
    try:
        active = embedder if embedder is not None else GroqEmbedder.from_env()
        return {**state, "embedding": active.embed(state["search_document"] or "")}
    except EmbedderError as exc:
        return {
            **state,
            "status": "error",
            "errors": [f"embedding failed: {exc}"],
        }
    except Exception as exc:
        return {
            **state,
            "status": "error",
            "errors": [f"embedding failed: {exc}"],
        }


def store_embedding(state: CRMState, store: ContactStore) -> CRMState:
    if state.get("status") in ("invalid", "error"):
        return state
    try:
        store.upsert_embedding(state["contact_id"], state["embedding"])
        return state
    except StoreError as exc:
        return {**state, "status": "error", "errors": [f"embedding store failed: {exc}"]}
    except Exception as exc:
        return {**state, "status": "error", "errors": [f"embedding store failed: {exc}"]}


def finalize(state: CRMState) -> CRMState:
    if (
        state.get("status") == "valid"
        and state.get("contact_evidence") is not None
        and state.get("contact_id") is not None
        and state.get("verified_contact") is not None
    ):
        return {**state, "status": "complete"}
    return state


def build_graph(
    extractor: CardExtractor | None = None,
    transcriber: VoiceTranscriber | None = None,
    store: ContactStore | None = None,
    db_path: str | Path | None = None,
    embedder: EmbeddingProvider | None = None,
):
    dim = embedder.dimension if embedder is not None else None
    active_store = (
        store
        if store is not None
        else ContactStore(db_path or DEFAULT_DB_PATH, embedding_dim=dim)
    )

    def extract_card_node(state: CRMState) -> CRMState:
        return extract_card(state, extractor)

    def transcribe_voice_node(state: CRMState) -> CRMState:
        return transcribe_voice(state, transcriber)

    def search_crm_node(state: CRMState) -> CRMState:
        return search_crm(state, active_store)

    def create_contact_node(state: CRMState) -> CRMState:
        return create_contact(state, active_store)

    def update_contact_node(state: CRMState) -> CRMState:
        return update_contact(state, active_store)

    def verify_write_node(state: CRMState) -> CRMState:
        return verify_write(state, active_store)

    def create_embedding_node(state: CRMState) -> CRMState:
        return create_embedding(state, embedder)

    def store_embedding_node(state: CRMState) -> CRMState:
        return store_embedding(state, active_store)

    graph = StateGraph(CRMState)
    graph.add_node("load_input", load_input)
    graph.add_node("validate_input", validate_input)
    graph.add_node("extract_card", extract_card_node)
    graph.add_node("validate_extraction", validate_extraction)
    graph.add_node("transcribe_voice", transcribe_voice_node)
    graph.add_node("merge_context", merge_context)
    graph.add_node("normalize_contact", normalize_contact)
    graph.add_node("search_crm", search_crm_node)
    graph.add_node("create_contact", create_contact_node)
    graph.add_node("update_contact", update_contact_node)
    graph.add_node("verify_write", verify_write_node)
    graph.add_node("build_search_document", build_search_document)
    graph.add_node("create_embedding", create_embedding_node)
    graph.add_node("store_embedding", store_embedding_node)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "load_input")
    graph.add_edge("load_input", "validate_input")
    graph.add_edge("validate_input", "extract_card")
    graph.add_edge("extract_card", "validate_extraction")
    graph.add_conditional_edges(
        "validate_extraction",
        voice_present,
        {
            "transcribe_voice": "transcribe_voice",
            "merge_context": "merge_context",
        },
    )
    graph.add_edge("transcribe_voice", "merge_context")
    graph.add_conditional_edges(
        "merge_context",
        persistable,
        {
            "normalize_contact": "normalize_contact",
            "finalize": "finalize",
        },
    )
    graph.add_edge("normalize_contact", "search_crm")
    graph.add_conditional_edges(
        "search_crm",
        match_found,
        {
            "update_contact": "update_contact",
            "create_contact": "create_contact",
            "finalize": "finalize",
        },
    )
    graph.add_edge("create_contact", "verify_write")
    graph.add_edge("update_contact", "verify_write")
    graph.add_conditional_edges(
        "verify_write",
        write_ok,
        {
            "write_ok": "build_search_document",
            "write_failed": "finalize",
        },
    )
    graph.add_edge("build_search_document", "create_embedding")
    graph.add_edge("create_embedding", "store_embedding")
    graph.add_edge("store_embedding", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
