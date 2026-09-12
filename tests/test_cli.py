import json
import subprocess
import sys

from crm.cli import main


def _touch_image(tmp_path) -> str:
    image = tmp_path / "card.jpg"
    image.write_bytes(b"placeholder")
    return str(image)


def test_cli_valid_prints_json_status(tmp_path, capsys) -> None:
    image = _touch_image(tmp_path)

    code = main(["--name", "Ada Lovelace", "--image", image])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["status"] == "complete"
    assert payload["errors"] == []


def test_cli_module_smoke_prints_status(tmp_path) -> None:
    image = _touch_image(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "crm",
            "--name",
            "Ada Lovelace",
            "--image",
            image,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "complete"


def test_cli_invalid_prints_json_and_exits_1(tmp_path, capsys) -> None:
    image = _touch_image(tmp_path)

    code = main(["--name", "   ", "--image", image])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["status"] == "invalid"
    assert payload["errors"]
