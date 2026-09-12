from pathlib import Path

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from crm.providers.base import CardExtractor, ExtractorError
from crm.providers.groq import GroqCardExtractor
from crm.schemas import ContactEvidence
from crm.state import CRMState


def _blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


def load_input(state: CRMState) -> CRMState:
    return {
        "name": state.get("name"),
        "image_path": state.get("image_path"),
        "voice_path": state.get("voice_path"),
        "status": "loaded",
        "errors": [],
        "contact_evidence": None,
        "extracted_card": None,
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


def finalize(state: CRMState) -> CRMState:
    if state.get("status") == "valid" and state.get("contact_evidence") is not None:
        return {**state, "status": "complete"}
    return state


def build_graph(extractor: CardExtractor | None = None):
    def extract_card_node(state: CRMState) -> CRMState:
        return extract_card(state, extractor)

    graph = StateGraph(CRMState)
    graph.add_node("load_input", load_input)
    graph.add_node("validate_input", validate_input)
    graph.add_node("extract_card", extract_card_node)
    graph.add_node("validate_extraction", validate_extraction)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "load_input")
    graph.add_edge("load_input", "validate_input")
    graph.add_edge("validate_input", "extract_card")
    graph.add_edge("extract_card", "validate_extraction")
    graph.add_edge("validate_extraction", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
