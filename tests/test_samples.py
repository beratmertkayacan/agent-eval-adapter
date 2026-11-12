import json
from pathlib import Path

import pytest

from adapter.models import InvokeRequest, RunRecord
from adapter.redaction import REDACTED

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

EXPECTED = {
    "run-0001": ("warehouse-agent", "awaiting_approval"),
    "run-0002": ("warehouse-agent", "manual_review"),
    "run-0003": ("warehouse-agent", "awaiting_approval"),
    "run-0004": ("warehouse-agent", "awaiting_approval"),
    "run-0005": ("mock-agent", "completed"),
}


def load_run(run_id: str) -> RunRecord:
    text = (SAMPLES_DIR / "runs" / f"{run_id}.json").read_text(encoding="utf-8")
    return RunRecord.model_validate(json.loads(text))


def load_request(name: str) -> InvokeRequest:
    text = (SAMPLES_DIR / "requests" / name).read_text(encoding="utf-8")
    return InvokeRequest.model_validate(json.loads(text))


def test_every_sample_run_is_listed():
    files = sorted(path.stem for path in (SAMPLES_DIR / "runs").glob("*.json"))

    assert files == sorted(EXPECTED)


@pytest.mark.parametrize("run_id", sorted(EXPECTED))
def test_sample_run_has_the_expected_agent_and_status(run_id):
    run = load_run(run_id)
    agent_id, status = EXPECTED[run_id]

    assert run.run_id == run_id
    assert run.agent_id == agent_id
    assert run.normalized_response.response.status == status
    assert run.http_status == 200
    assert run.error is None
    assert run.raw_response is not None


def test_case_1_valid_request_waits_for_approval():
    run = load_run("run-0001")

    assert run.request.input == load_request("case1_valid.json").input
    assert run.normalized_response.observability.approval["status"] == "pending"


def test_case_2_invalid_request_goes_to_manual_review():
    run = load_run("run-0002")

    assert run.request.input == load_request("case2_invalid.json").input
    assert run.normalized_response.observability.approval is None


def test_case_3_second_message_uses_the_same_session():
    first = load_run("run-0001")
    second = load_run("run-0003")

    assert load_request("case3_second_message.json").previous_run_id == "run-0001"
    assert second.session_id == first.session_id
    assert second.request.body["sessionId"] == first.session_id
    assert second.previous_run_id == "run-0001"
    assert second.turn == 2


def test_case_4_replay_is_a_new_run_with_the_same_request():
    original = load_run("run-0001")
    replay = load_run("run-0004")

    assert replay.replay_of == "run-0001"
    assert replay.request == original.request
    assert replay.run_id != original.run_id


def test_second_agent_sample_is_normalized_and_redacted():
    run = load_run("run-0005")

    assert run.request.input == load_request("case5_mock_agent.json").input
    assert isinstance(run.normalized_response.response.answer, dict)
    assert run.raw_response["debug"]["token"] == REDACTED


def test_sample_runs_do_not_contain_the_mock_token():
    for path in (SAMPLES_DIR / "runs").glob("*.json"):
        assert "mock-token-123" not in path.read_text(encoding="utf-8")
