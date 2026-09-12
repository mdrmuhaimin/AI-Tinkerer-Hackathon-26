import json
import os
from pathlib import Path

import pytest

from crm.eval import (
    DATASET_PATH,
    EVALUATOR_KEYS,
    create_vs_update,
    duplicate_avoidance,
    extraction_correctness,
    load_dataset,
    post_write_verification,
    run_experiment,
    unsupported_field_hallucination,
    weakest_example,
)
from crm.tracing import enable_tracing

REQUIRED_SCENARIOS = {
    "complete business card",
    "partially populated card",
    "missing phone",
    "missing email",
    "existing contact",
    "new contact",
    "voice note present",
    "voice note absent",
    "conflicting information",
    "unsupported information",
}

_PASS_EVIDENCE = {
    "full_name": "Ada Lovelace",
    "company": "Analytical Engines",
    "email": "ada@example.com",
    "phone": None,
}


def test_dataset_contains_all_scenario_tags() -> None:
    examples = load_dataset()
    tags = {tag for example in examples for tag in example["scenarios"]}
    assert REQUIRED_SCENARIOS <= tags
    assert DATASET_PATH.is_file()


def test_extraction_correctness_pass() -> None:
    result = extraction_correctness(
        outputs={"contact_evidence": _PASS_EVIDENCE},
        reference_outputs={"contact_evidence": _PASS_EVIDENCE},
    )
    assert result["key"] == "extraction_correctness"
    assert result["score"] == 1.0


def test_extraction_correctness_fail() -> None:
    result = extraction_correctness(
        outputs={
            "contact_evidence": {**_PASS_EVIDENCE, "company": "Wrong Co"},
        },
        reference_outputs={"contact_evidence": _PASS_EVIDENCE},
    )
    assert result["key"] == "extraction_correctness"
    assert result["score"] == 0.75


def test_unsupported_field_hallucination_pass() -> None:
    result = unsupported_field_hallucination(
        outputs={"contact_evidence": _PASS_EVIDENCE},
        reference_outputs={"null_fields": ["phone", "website", "address"]},
    )
    assert result["key"] == "unsupported_field_hallucination"
    assert result["score"] == 1.0


def test_unsupported_field_hallucination_fail() -> None:
    result = unsupported_field_hallucination(
        outputs={
            "contact_evidence": {**_PASS_EVIDENCE, "website": "https://invented.example"},
        },
        reference_outputs={"null_fields": ["phone", "website"]},
    )
    assert result["key"] == "unsupported_field_hallucination"
    assert result["score"] == 0.5


def test_create_vs_update_pass() -> None:
    result = create_vs_update(
        outputs={"crm_action": "updated"},
        reference_outputs={"crm_action": "updated"},
    )
    assert result["key"] == "create_vs_update"
    assert result["score"] == 1.0


def test_create_vs_update_fail() -> None:
    result = create_vs_update(
        outputs={"crm_action": "created"},
        reference_outputs={"crm_action": "updated"},
    )
    assert result["key"] == "create_vs_update"
    assert result["score"] == 0.0


def test_duplicate_avoidance_pass_existing() -> None:
    result = duplicate_avoidance(
        outputs={
            "crm_action": "updated",
            "contact_id": 1,
            "seeded_id": 1,
            "row_count": 1,
        },
        reference_outputs={"crm_action": "updated"},
    )
    assert result["key"] == "duplicate_avoidance"
    assert result["score"] == 1.0


def test_duplicate_avoidance_fail_existing() -> None:
    result = duplicate_avoidance(
        outputs={
            "crm_action": "created",
            "contact_id": 2,
            "seeded_id": 1,
            "row_count": 2,
        },
        reference_outputs={"crm_action": "updated"},
    )
    assert result["key"] == "duplicate_avoidance"
    assert result["score"] < 1.0


def test_duplicate_avoidance_pass_new() -> None:
    result = duplicate_avoidance(
        outputs={
            "crm_action": "created",
            "contact_id": 2,
            "seeded_id": 1,
            "row_count": 2,
        },
        reference_outputs={"crm_action": "created"},
    )
    assert result["key"] == "duplicate_avoidance"
    assert result["score"] == 1.0


def test_duplicate_avoidance_fail_new() -> None:
    result = duplicate_avoidance(
        outputs={
            "crm_action": "updated",
            "contact_id": 1,
            "seeded_id": 1,
            "row_count": 1,
        },
        reference_outputs={"crm_action": "created"},
    )
    assert result["key"] == "duplicate_avoidance"
    assert result["score"] < 1.0


def test_post_write_verification_pass() -> None:
    result = post_write_verification(
        outputs={"verified_contact": {"id": 1}, "status": "complete"},
        reference_outputs={"verified": True},
    )
    assert result["key"] == "post_write_verification"
    assert result["score"] == 1.0


def test_post_write_verification_fail() -> None:
    result = post_write_verification(
        outputs={"verified_contact": None, "status": "error"},
        reference_outputs={"verified": True},
    )
    assert result["key"] == "post_write_verification"
    assert result["score"] == 0.0


def test_local_eval_scores_every_example(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    out = tmp_path / "latest_experiment.json"
    payload = run_experiment(results_path=out)
    expected_ids = {example["id"] for example in load_dataset()}
    got_ids = {row["id"] for row in payload["examples"]}
    assert got_ids == expected_ids
    for row in payload["examples"]:
        for key in EVALUATOR_KEYS:
            assert key in row["scores"]
            assert 0.0 <= row["scores"][key] <= 1.0
    assert out.is_file()
    saved = json.loads(out.read_text())
    assert saved["examples"]
    weak = saved["weakest_example"]
    assert weak["id"]
    assert "mean" in weak
    assert weak["why"]
    assert payload["weakest_example"] == weak


def test_weakest_example_prefers_conflicting_voice_on_tie() -> None:
    ones = {key: 1.0 for key in EVALUATOR_KEYS}
    rows = [{"id": "complete-card", "scores": ones}, {"id": "conflicting-voice", "scores": ones}]
    weak = weakest_example(rows)
    assert weak["id"] == "conflicting-voice"
    assert weak["mean"] == 1.0
    assert "card identity" in weak["why"].lower()
    assert "voice" in weak["why"].lower()


def test_default_eval_does_not_upload_or_create_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

    def boom(*_args, **_kwargs):
        raise AssertionError("LangSmith dataset/upload called")

    monkeypatch.setattr("langsmith.Client.create_dataset", boom)
    monkeypatch.setattr("langsmith.Client.create_examples", boom)

    seen: list[bool] = []
    from langsmith import evaluate as real_evaluate

    def wrapped(*args, **kwargs):
        seen.append(kwargs.get("upload_results"))
        return real_evaluate(*args, **kwargs)

    monkeypatch.setattr("crm.eval.evaluate", wrapped)
    payload = run_experiment(results_path=tmp_path / "latest.json")
    assert seen == [False]
    assert payload["experiment_url"] is None
    assert os.environ.get("LANGSMITH_API_KEY") is None
    assert os.environ.get("LANGSMITH_TRACING", "").lower() == "false"
    assert os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "false"


def test_enable_tracing_noop_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.setattr("crm.tracing.load_dotenv", lambda: None)
    enable_tracing()
    assert os.environ.get("LANGSMITH_TRACING") in (None, "")


def test_enable_tracing_sets_flags_when_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-not-a-real-key")
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.setattr("crm.tracing.load_dotenv", lambda: None)
    enable_tracing()
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_PROJECT"] == "ai-conference-crm"
