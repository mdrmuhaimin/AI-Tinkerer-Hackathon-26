from pathlib import Path

from crm.graph import build_graph
from crm.state import CRMState


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
    }


def _touch(path: Path) -> str:
    path.write_bytes(b"placeholder")
    return str(path)


def test_valid_name_and_image_completes(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    graph = build_graph()

    result = graph.invoke(_pending(name="Ada Lovelace", image_path=image))

    assert result["status"] == "complete"
    assert result["errors"] == []
    assert result["name"] == "Ada Lovelace"
    assert result["image_path"] == image


def test_missing_or_blank_name_is_invalid(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    graph = build_graph()

    missing = graph.invoke(_pending(name=None, image_path=image))
    assert missing["status"] == "invalid"
    assert missing["errors"]
    assert any("name" in error.lower() for error in missing["errors"])

    blank = graph.invoke(_pending(name="   ", image_path=image))
    assert blank["status"] == "invalid"
    assert blank["errors"]
    assert any("name" in error.lower() for error in blank["errors"])


def test_missing_or_nonexistent_image_is_invalid() -> None:
    graph = build_graph()

    missing = graph.invoke(_pending(name="Ada Lovelace", image_path=None))
    assert missing["status"] == "invalid"
    assert missing["errors"]
    assert any("image" in error.lower() for error in missing["errors"])

    missing_file = graph.invoke(
        _pending(name="Ada Lovelace", image_path="/definitely/not/a/file.jpg")
    )
    assert missing_file["status"] == "invalid"
    assert missing_file["errors"]
    assert any("image" in error.lower() for error in missing_file["errors"])


def test_voice_path_optional_and_kept_when_present(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "note.wav")
    graph = build_graph()

    without_voice = graph.invoke(
        _pending(name="Ada Lovelace", image_path=image, voice_path=None)
    )
    assert without_voice["status"] == "complete"
    assert without_voice["errors"] == []
    assert without_voice["voice_path"] in (None, "")

    blank_voice = graph.invoke(
        _pending(name="Ada Lovelace", image_path=image, voice_path="  ")
    )
    assert blank_voice["status"] == "complete"
    assert blank_voice["errors"] == []

    with_voice = graph.invoke(
        _pending(name="Ada Lovelace", image_path=image, voice_path=voice)
    )
    assert with_voice["status"] == "complete"
    assert with_voice["errors"] == []
    assert with_voice["voice_path"] == voice

    missing_voice = graph.invoke(
        _pending(
            name="Ada Lovelace",
            image_path=image,
            voice_path=str(tmp_path / "missing.wav"),
        )
    )
    assert missing_voice["status"] == "invalid"
    assert missing_voice["errors"]
    assert any("voice" in error.lower() for error in missing_voice["errors"])


def _stream_node_names(graph, state: CRMState) -> list[str]:
    return [next(iter(chunk)) for chunk in graph.stream(state)]


def test_stream_node_order_valid_and_invalid(tmp_path: Path) -> None:
    image = _touch(tmp_path / "card.jpg")
    graph = build_graph()
    expected = ["load_input", "validate_input", "finalize"]

    valid_state = _pending(name="Ada Lovelace", image_path=image)
    assert _stream_node_names(graph, valid_state) == expected

    valid_events = list(graph.stream(valid_state))
    assert valid_events[0]["load_input"]["status"] == "loaded"
    assert valid_events[1]["validate_input"]["status"] == "valid"
    assert valid_events[2]["finalize"]["status"] == "complete"

    invalid_state = _pending(name=None, image_path=image)
    assert _stream_node_names(graph, invalid_state) == expected

    invalid_events = list(graph.stream(invalid_state))
    assert invalid_events[0]["load_input"]["status"] == "loaded"
    assert invalid_events[1]["validate_input"]["status"] == "invalid"
    assert invalid_events[2]["finalize"]["status"] == "invalid"
