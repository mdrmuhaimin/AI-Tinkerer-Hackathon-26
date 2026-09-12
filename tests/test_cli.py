import json
import subprocess
import sys

from crm.cli import main
from crm.graph import build_graph
from crm.providers.base import ExtractorError
from tests.helpers import FakeEmbedder, FakeExtractor, FakeTranscriber


def _touch_image(tmp_path) -> str:
    image = tmp_path / "card.jpg"
    image.write_bytes(b"placeholder")
    return str(image)


def _patch_graph(
    monkeypatch,
    tmp_path,
    extractor: FakeExtractor,
    transcriber: FakeTranscriber | None = None,
) -> None:
    if transcriber is None:
        transcriber = FakeTranscriber()
    monkeypatch.setattr(
        "crm.cli.build_graph",
        lambda: build_graph(
            extractor=extractor,
            transcriber=transcriber,
            db_path=tmp_path / "crm.db",
            embedder=FakeEmbedder(),
        ),
    )


def test_cli_valid_prints_json_status(tmp_path, capsys, monkeypatch) -> None:
    image = _touch_image(tmp_path)
    fake = FakeExtractor(
        {
            "full_name": "Ada Lovelace",
            "company": "Analytical Engines",
            "job_title": None,
            "email": None,
            "phone": None,
            "website": None,
            "address": None,
        }
    )
    _patch_graph(monkeypatch, tmp_path, fake)

    code = main(["--name", "Ada Lovelace", "--image", image])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["status"] == "complete"
    assert payload["errors"] == []
    assert payload["contact_evidence"]["full_name"] == "Ada Lovelace"
    assert payload["contact_evidence"]["company"] == "Analytical Engines"
    assert payload["voice_transcript"] is None
    assert payload["conversation_notes"] is None


def test_cli_module_smoke_invalid_avoids_provider(tmp_path) -> None:
    image = _touch_image(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "crm",
            "--name",
            "   ",
            "--image",
            image,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "invalid"
    assert payload["errors"]
    assert payload.get("contact_evidence") is None


def test_cli_invalid_prints_json_and_exits_1(tmp_path, capsys, monkeypatch) -> None:
    image = _touch_image(tmp_path)
    fake = FakeExtractor({"full_name": "Ada Lovelace"})
    _patch_graph(monkeypatch, tmp_path, fake)

    code = main(["--name", "   ", "--image", image])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["status"] == "invalid"
    assert payload["errors"]
    assert payload["contact_evidence"] is None
    assert fake.calls == []


def test_cli_voice_prints_transcript_and_notes(tmp_path, capsys, monkeypatch) -> None:
    image = _touch_image(tmp_path)
    voice = tmp_path / "sarah_note.ogg"
    voice.write_bytes(b"placeholder")
    fake = FakeExtractor({"full_name": "Ada Lovelace"})
    transcriber = FakeTranscriber(
        "Met Sarah at AI Tinkerer Hackathon.\n"
        "She is interested in AI workflow automation for product teams.\n"
        "We discussed a possible pilot.\n"
        "Follow up next week and send her the demo."
    )
    _patch_graph(monkeypatch, tmp_path, fake, transcriber)

    code = main(["--name", "Ada Lovelace", "--image", image, "--voice", str(voice)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "complete"
    assert payload["voice_transcript"] == transcriber.transcript
    assert payload["conversation_notes"] == transcriber.transcript
    assert transcriber.calls == [str(voice)]


def test_cli_notes_stored(tmp_path, capsys, monkeypatch) -> None:
    image = _touch_image(tmp_path)
    fake = FakeExtractor({"full_name": "Ada Lovelace"})
    _patch_graph(monkeypatch, tmp_path, fake)

    code = main(
        ["--name", "Ada Lovelace", "--image", image, "--notes", "Met at AI Tinkerer."]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "complete"
    assert payload["conversation_notes"] == "Met at AI Tinkerer."
    assert payload["voice_transcript"] is None


def test_cli_notes_and_voice_merge(tmp_path, capsys, monkeypatch) -> None:
    image = _touch_image(tmp_path)
    voice = tmp_path / "sarah_note.ogg"
    voice.write_bytes(b"placeholder")
    fake = FakeExtractor({"full_name": "Ada Lovelace"})
    transcriber = FakeTranscriber("Met at LEAP. Discussed data warehouse modernization.")
    _patch_graph(monkeypatch, tmp_path, fake, transcriber)

    code = main(
        [
            "--name",
            "Ada Lovelace",
            "--image",
            image,
            "--notes",
            "Potential consulting lead.",
            "--voice",
            str(voice),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["voice_transcript"] == transcriber.transcript
    assert payload["conversation_notes"] == (
        "Potential consulting lead.\n\n" + transcriber.transcript
    )


def test_query_ranked_list_does_not_run_graph_or_write(
    tmp_path, capsys, monkeypatch
) -> None:
    from tests.test_crm import SARAH, _count, _run
    from tests.test_embeddings import DECOY, DECOY_NOTES, RELATED_QUERY, WORKFLOW_NOTES

    first, store = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES)
    _run(tmp_path, DECOY, transcript=DECOY_NOTES, store=store)
    before = _count(store)

    def boom(*_args, **_kwargs):
        raise AssertionError("capture graph invoked")

    monkeypatch.setattr("crm.cli.build_graph", boom)

    code = main(
        ["query", RELATED_QUERY],
        embedder=FakeEmbedder(),
        store=store,
    )
    out = capsys.readouterr().out

    assert code == 0
    assert "1. Sarah Khan" in out
    assert "NexaTech Solutions" in out
    assert WORKFLOW_NOTES.split()[0] in out or "workflow" in out.lower()
    assert not out.lstrip().startswith("{")
    assert not out.lstrip().startswith("[")
    assert _count(store) == before
    assert store.get(first["contact_id"])["full_name"] == "Sarah Khan"


def test_cli_extractor_error_exits_1(tmp_path, capsys, monkeypatch) -> None:
    image = _touch_image(tmp_path)
    fake = FakeExtractor(error=ExtractorError("provider unavailable"))
    _patch_graph(monkeypatch, tmp_path, fake)

    code = main(["--name", "Ada Lovelace", "--image", image])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["status"] == "error"
    assert payload["errors"]
    assert payload["contact_evidence"] is None
