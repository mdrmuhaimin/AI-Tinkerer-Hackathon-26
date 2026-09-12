from pathlib import Path

from langgraph.graph import END, START, StateGraph

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


def finalize(state: CRMState) -> CRMState:
    if state.get("status") == "valid":
        return {**state, "status": "complete"}
    return state


def build_graph():
    graph = StateGraph(CRMState)
    graph.add_node("load_input", load_input)
    graph.add_node("validate_input", validate_input)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "load_input")
    graph.add_edge("load_input", "validate_input")
    graph.add_edge("validate_input", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
