import json
import subprocess
import sys

from crm.cli import main
from crm.graph import build_graph
from crm.providers.base import ExtractorError
from tests.helpers import FakeExtractor


def _touch_image(tmp_path) -> str:
    image = tmp_path / "card.jpg"
    image.write_bytes(b"placeholder")
    return str(image)


def _patch_graph(monkeypatch, extractor: FakeExtractor) -> None:
    monkeypatch.setattr("crm.cli.build_graph", lambda: build_graph(extractor=extractor))


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
    _patch_graph(monkeypatch, fake)

    code = main(["--name", "Ada Lovelace", "--image", image])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["status"] == "complete"
    assert payload["errors"] == []
    assert payload["contact_evidence"]["full_name"] == "Ada Lovelace"
    assert payload["contact_evidence"]["company"] == "Analytical Engines"


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
    _patch_graph(monkeypatch, fake)

    code = main(["--name", "   ", "--image", image])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["status"] == "invalid"
    assert payload["errors"]
    assert payload["contact_evidence"] is None
    assert fake.calls == []


def test_cli_extractor_error_exits_1(tmp_path, capsys, monkeypatch) -> None:
    image = _touch_image(tmp_path)
    fake = FakeExtractor(error=ExtractorError("provider unavailable"))
    _patch_graph(monkeypatch, fake)

    code = main(["--name", "Ada Lovelace", "--image", image])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["status"] == "error"
    assert payload["errors"]
    assert payload["contact_evidence"] is None
