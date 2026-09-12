from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import sys

from dotenv import load_dotenv
from langsmith import Client, evaluate
from langsmith.schemas import Example

from crm.db import ContactStore
from crm.graph import build_graph

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from tests.helpers import FakeEmbedder, FakeExtractor, FakeTranscriber

DATASET_PATH = REPO_ROOT / "eval" / "dataset.json"
RESULTS_PATH = REPO_ROOT / "eval" / "latest_experiment.json"
EVALUATOR_KEYS = (
    "extraction_correctness",
    "unsupported_field_hallucination",
    "create_vs_update",
    "duplicate_avoidance",
    "post_write_verification",
)


def load_dataset(path: Path = DATASET_PATH) -> list[dict]:
    return json.loads(path.read_text())["examples"]


def run_capture(inputs: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        store = ContactStore(tmp_path / "crm.db")
        seed = inputs.get("seed_contact")
        seeded_id = store.create(seed) if seed else None
        image = tmp_path / "card.jpg"
        image.write_bytes(b"placeholder")
        transcript = inputs.get("voice_transcript")
        voice_path = None
        transcriber = FakeTranscriber()
        if transcript is not None:
            voice = tmp_path / "note.ogg"
            voice.write_bytes(b"placeholder")
            voice_path = str(voice)
            transcriber = FakeTranscriber(transcript)
        graph = build_graph(
            extractor=FakeExtractor(inputs.get("card") or {}),
            transcriber=transcriber,
            store=store,
            embedder=FakeEmbedder(),
        )
        result = graph.invoke(
            {
                "name": inputs.get("name"),
                "image_path": str(image),
                "voice_path": voice_path,
                "status": "pending",
                "errors": [],
                "contact_evidence": None,
                "extracted_card": None,
                "voice_transcript": None,
                "conversation_notes": None,
            }
        )
        with sqlite3.connect(store.db_path) as conn:
            row_count = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        return {
            "example_id": inputs.get("example_id"),
            "contact_evidence": result.get("contact_evidence"),
            "crm_action": result.get("crm_action"),
            "contact_id": result.get("contact_id"),
            "status": result.get("status"),
            "verified_contact": result.get("verified_contact"),
            "conversation_notes": result.get("conversation_notes"),
            "errors": result.get("errors") or [],
            "row_count": row_count,
            "seeded_id": seeded_id,
        }


def extraction_correctness(
    inputs: dict | None = None,
    outputs: dict | None = None,
    reference_outputs: dict | None = None,
) -> dict:
    predicted = (outputs or {}).get("contact_evidence") or {}
    expected = (reference_outputs or {}).get("contact_evidence") or {}
    if not expected:
        return {"key": "extraction_correctness", "score": 1.0}
    hits = sum(1 for key, want in expected.items() if predicted.get(key) == want)
    return {"key": "extraction_correctness", "score": hits / len(expected)}


def unsupported_field_hallucination(
    inputs: dict | None = None,
    outputs: dict | None = None,
    reference_outputs: dict | None = None,
) -> dict:
    fields = (reference_outputs or {}).get("null_fields") or []
    if not fields:
        return {"key": "unsupported_field_hallucination", "score": 1.0}
    evidence = (outputs or {}).get("contact_evidence") or {}
    hits = sum(1 for field in fields if evidence.get(field) is None)
    return {"key": "unsupported_field_hallucination", "score": hits / len(fields)}


def create_vs_update(
    inputs: dict | None = None,
    outputs: dict | None = None,
    reference_outputs: dict | None = None,
) -> dict:
    score = (
        1.0
        if (outputs or {}).get("crm_action") == (reference_outputs or {}).get("crm_action")
        else 0.0
    )
    return {"key": "create_vs_update", "score": score}


def duplicate_avoidance(
    inputs: dict | None = None,
    outputs: dict | None = None,
    reference_outputs: dict | None = None,
) -> dict:
    outputs = outputs or {}
    expected = (reference_outputs or {}).get("crm_action")
    contact_id = outputs.get("contact_id")
    seeded_id = outputs.get("seeded_id")
    row_count = outputs.get("row_count")
    action = outputs.get("crm_action")
    if expected == "updated":
        checks = [
            action == "updated",
            seeded_id is not None and contact_id == seeded_id,
            row_count == 1,
        ]
    else:
        checks = [
            action == "created",
            seeded_id is None or contact_id != seeded_id,
            row_count == (2 if seeded_id is not None else 1),
        ]
    return {"key": "duplicate_avoidance", "score": sum(checks) / len(checks)}


def post_write_verification(
    inputs: dict | None = None,
    outputs: dict | None = None,
    reference_outputs: dict | None = None,
) -> dict:
    outputs = outputs or {}
    if (reference_outputs or {}).get("verified"):
        checks = [
            outputs.get("verified_contact") is not None,
            outputs.get("status") == "complete",
        ]
    else:
        checks = [
            outputs.get("verified_contact") is None,
            outputs.get("status") != "complete",
        ]
    return {"key": "post_write_verification", "score": sum(checks) / len(checks)}


def _eval_items(results) -> list:
    return list(results)


def _scores_from_item(item: dict) -> dict[str, float]:
    raw = item["evaluation_results"]
    rows = raw.results if hasattr(raw, "results") else raw["results"]
    scores = {}
    for row in rows:
        key = getattr(row, "key", None) or row["key"]
        score = getattr(row, "score", None) if hasattr(row, "score") else row["score"]
        scores[key] = float(score)
    return scores


def _example_id(item: dict) -> str:
    run = item.get("run")
    example = item.get("example")
    outputs = getattr(run, "outputs", None) or {}
    inputs = getattr(example, "inputs", None) or {}
    return outputs.get("example_id") or inputs.get("example_id")


TIEBREAK_ID = "conflicting-voice"
TIEBREAK_WHY = (
    "fakes make every score 1.0; this case is still the hardest because a live "
    "extract or sloppy merge could overwrite card company/email from the voice "
    "note. Card identity must win; notes keep the voice."
)


def _row_mean(row: dict) -> float:
    scores = row.get("scores") or {}
    return sum(scores.get(key, 0.0) for key in EVALUATOR_KEYS) / len(EVALUATOR_KEYS)


def weakest_example(examples: list[dict]) -> dict:
    low = min(_row_mean(row) for row in examples)
    tied = [row for row in examples if _row_mean(row) == low]
    chosen = next((row for row in tied if row["id"] == TIEBREAK_ID), tied[0])
    why = (
        TIEBREAK_WHY
        if chosen["id"] == TIEBREAK_ID
        else f"lowest mean among examples ({low})"
    )
    return {"id": chosen["id"], "mean": low, "why": why}


def _experiment_url(results) -> str | None:
    for attr in ("experiment_url", "url"):
        value = getattr(results, attr, None)
        if value:
            return str(value)
    manager = getattr(results, "_manager", None)
    experiment = getattr(manager, "_experiment", None) if manager else None
    url = getattr(experiment, "url", None) or getattr(experiment, "app_url", None)
    return str(url) if url else None


def run_experiment(results_path: Path | None = None) -> dict:
    load_dotenv()
    upload_results = bool(os.environ.get("LANGSMITH_API_KEY"))
    if not upload_results:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        client = Client(
            auto_batch_tracing=False,
            info={"version": "0.0.0"},
            tracing_sampling_rate=0,
        )
    else:
        client = None
    now = datetime.now(timezone.utc)
    data = [
        Example(
            id=uuid5(NAMESPACE_URL, example["id"]),
            inputs={**example["inputs"], "example_id": example["id"]},
            outputs=example["outputs"],
            created_at=now,
            modified_at=now,
        )
        for example in load_dataset()
    ]
    results = evaluate(
        run_capture,
        data=data,
        evaluators=[
            extraction_correctness,
            unsupported_field_hallucination,
            create_vs_update,
            duplicate_avoidance,
            post_write_verification,
        ],
        experiment_prefix="crm-capture",
        upload_results=upload_results,
        client=client,
    )
    examples = []
    for item in _eval_items(results):
        scores = _scores_from_item(item)
        examples.append({"id": _example_id(item), "scores": scores})
    mean_scores = {
        key: sum(row["scores"].get(key, 0.0) for row in examples) / len(examples)
        for key in EVALUATOR_KEYS
    }
    payload = {
        "examples": examples,
        "mean_scores": mean_scores,
        "experiment_url": _experiment_url(results) if upload_results else None,
        "weakest_example": weakest_example(examples),
    }
    dest = Path(results_path) if results_path is not None else RESULTS_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def _print_table(payload: dict) -> None:
    short = {
        "extraction_correctness": "extract",
        "unsupported_field_hallucination": "nulls",
        "create_vs_update": "action",
        "duplicate_avoidance": "dup",
        "post_write_verification": "verify",
    }
    headers = ["id", *[short[key] for key in EVALUATOR_KEYS]]
    print("  ".join(f"{name:12}" for name in headers))
    for row in payload["examples"]:
        cells = [f"{row['id']:12}"]
        cells.extend(f"{row['scores'].get(key, 0):12.2f}" for key in EVALUATOR_KEYS)
        print("  ".join(cells))
    means = payload["mean_scores"]
    cells = [f"{'mean':12}"]
    cells.extend(f"{means[key]:12.2f}" for key in EVALUATOR_KEYS)
    print("  ".join(cells))
    url = payload.get("experiment_url")
    print(f"experiment_url: {url}" if url else "experiment_url: (local, not uploaded)")
    weak = payload["weakest_example"]
    print(f"weakest_example: {weak['id']} (mean {weak['mean']})")
    print(f"why: {weak['why']}")


def main() -> int:
    _print_table(run_experiment())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
