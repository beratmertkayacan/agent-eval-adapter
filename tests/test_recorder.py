import json

import pytest

from adapter.client import CallResult
from adapter.models import AgentConfig, RecordedRequest
from adapter.normalize import build_run
from adapter.recorder import RunNotFoundError, RunRecorder
from adapter.redaction import REDACTED

AGENT = AgentConfig.model_validate(
    {
        "agentId": "test-agent",
        "request": {"endpoint": "/chat"},
        "responseMapping": {"answer": "answer", "status": "status"},
    }
)


def make_run(run_id: str, raw=None, body=None):
    raw = raw or {"answer": "ok", "status": "awaiting_approval"}
    request = RecordedRequest(input="hello", body=body or {"message": "hello"})
    return build_run(run_id, AGENT, request, CallResult(200, raw, 10, None))


@pytest.fixture
def recorder(tmp_path):
    return RunRecorder(tmp_path / "runs")


def test_first_run_id_is_run_0001(recorder):
    assert recorder.next_run_id() == "run-0001"


def test_saved_run_is_written_as_json(recorder):
    recorder.save(make_run("run-0001"))

    data = json.loads((recorder.runs_dir / "run-0001.json").read_text())
    assert data["runId"] == "run-0001"
    assert data["agentId"] == "test-agent"
    assert data["httpStatus"] == 200
    assert data["rawResponse"] == {"answer": "ok", "status": "awaiting_approval"}
    assert data["normalizedResponse"]["response"]["status"] == "awaiting_approval"
    for key in ["sessionId", "request", "latencyMs", "timestamp", "error"]:
        assert key in data


def test_run_ids_count_up(recorder):
    recorder.save(make_run(recorder.next_run_id()))
    recorder.save(make_run(recorder.next_run_id()))

    assert recorder.next_run_id() == "run-0003"
    assert [run.run_id for run in recorder.list_runs()] == ["run-0001", "run-0002"]


def test_get_returns_a_saved_run(recorder):
    recorder.save(make_run("run-0001"))

    assert recorder.get("run-0001").normalized_response.response.answer == "ok"


@pytest.mark.parametrize("run_id", ["run-0009", "../secret", "run-1"])
def test_unknown_run_raises_not_found(recorder, run_id):
    with pytest.raises(RunNotFoundError):
        recorder.get(run_id)


def test_existing_run_is_never_overwritten(recorder):
    recorder.save(make_run("run-0001"))

    with pytest.raises(FileExistsError):
        recorder.save(make_run("run-0001"))


def test_sensitive_values_are_not_written_to_disk(recorder):
    run = make_run(
        "run-0001",
        raw={"answer": "ok", "status": "done", "token": "t-123"},
        body={"message": "hello", "apiKey": "sk-123"},
    )

    saved = recorder.save(run, extra_fields=["message"])

    text = (recorder.runs_dir / "run-0001.json").read_text()
    assert "sk-123" not in text and "t-123" not in text
    assert saved.request.body == {"message": REDACTED, "apiKey": REDACTED}
    assert saved.raw_response["token"] == REDACTED


def test_list_is_empty_without_runs(recorder):
    assert recorder.list_runs() == []


def test_runs_are_sorted_by_number(recorder):
    for number in [2, 10, 1]:
        recorder.save(make_run(f"run-{number:04d}"))

    assert [run.run_id for run in recorder.list_runs()] == ["run-0001", "run-0002", "run-0010"]
