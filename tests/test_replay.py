import httpx2
import pytest

from adapter.models import InvokeRequest
from adapter.recorder import RunNotFoundError
from tests.fakes import INVALID_DOCUMENT, VALID_DOCUMENT


def invoke(service, text, previous_run_id=None):
    return service.invoke(
        "warehouse-agent", InvokeRequest(input=text, previous_run_id=previous_run_id)
    )


def test_replay_sends_the_original_request_again(service):
    seen = []

    def handler(request):
        seen.append(request.content)
        return httpx2.Response(200, json={"answer": "ok", "status": "manual_review"})

    original = invoke(service, VALID_DOCUMENT)
    service.transport = httpx2.MockTransport(handler)

    replay = service.replay(original.run_id)

    assert replay.request == original.request
    assert len(seen) == 1
    assert replay.raw_response["status"] == "manual_review"


def test_replay_is_stored_as_a_new_run(service):
    original = invoke(service, VALID_DOCUMENT)

    replay = service.replay(original.run_id)

    assert replay.run_id == "run-0002"
    assert replay.replay_of == "run-0001"
    assert [run.run_id for run in service.list_runs()] == ["run-0001", "run-0002"]


def test_original_run_is_not_changed(service):
    original = invoke(service, VALID_DOCUMENT)
    before = (service.recorder.runs_dir / "run-0001.json").read_text()

    service.replay(original.run_id)

    assert (service.recorder.runs_dir / "run-0001.json").read_text() == before
    assert service.get_run("run-0001").replay_of is None


def test_replay_of_a_later_turn_keeps_its_session_and_turn(service):
    first = invoke(service, VALID_DOCUMENT)
    second = invoke(service, INVALID_DOCUMENT, previous_run_id=first.run_id)

    replay = service.replay(second.run_id)

    assert replay.request.body["sessionId"] == "sess-001"
    assert replay.session_id == "sess-001"
    assert replay.turn == 2
    assert replay.previous_run_id == first.run_id


def test_replay_of_unknown_run_is_not_found(service):
    with pytest.raises(RunNotFoundError):
        service.replay("run-0099")
