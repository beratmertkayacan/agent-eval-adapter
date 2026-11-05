import httpx2
import pytest

from adapter.agent_config import AgentNotFoundError, load_agent
from adapter.models import AgentConfig, InvokeRequest
from adapter.recorder import RunNotFoundError, RunRecorder
from adapter.service import AdapterService, InvalidRequestError, build_body
from tests.fakes import INVALID_DOCUMENT, VALID_DOCUMENT


def invoke(service, text, previous_run_id=None):
    request = InvokeRequest(input=text, previous_run_id=previous_run_id)
    return service.invoke("warehouse-agent", request)


def test_text_input_is_sent_in_the_configured_field(service):
    run = invoke(service, VALID_DOCUMENT)

    assert run.request.body == {"message": VALID_DOCUMENT}
    assert run.normalized_response.response.status == "awaiting_approval"


def test_invalid_document_is_manual_review(service):
    run = invoke(service, INVALID_DOCUMENT)

    assert run.normalized_response.response.status == "manual_review"
    assert run.normalized_response.observability.approval is None


def test_every_invocation_is_recorded(service):
    first = invoke(service, VALID_DOCUMENT)
    second = invoke(service, INVALID_DOCUMENT)

    assert [first.run_id, second.run_id] == ["run-0001", "run-0002"]
    assert [run.run_id for run in service.list_runs()] == ["run-0001", "run-0002"]
    assert service.get_run("run-0001").run_id == "run-0001"


def test_first_turn_has_no_previous_run(service):
    run = invoke(service, VALID_DOCUMENT)

    assert run.turn == 1
    assert run.previous_run_id is None
    assert run.request.session_id is None
    assert run.session_id == "sess-001"


def test_session_from_previous_run_is_reused(service):
    first = invoke(service, VALID_DOCUMENT)
    second = invoke(service, INVALID_DOCUMENT, previous_run_id=first.run_id)
    third = invoke(service, VALID_DOCUMENT, previous_run_id=second.run_id)

    assert second.request.body == {"message": INVALID_DOCUMENT, "sessionId": "sess-001"}
    assert [run.session_id for run in [first, second, third]] == ["sess-001"] * 3
    assert [run.turn for run in [first, second, third]] == [1, 2, 3]
    assert third.previous_run_id == second.run_id
    assert [run.run_id for run in service.session_runs("sess-001")] == [
        "run-0001",
        "run-0002",
        "run-0003",
    ]


def test_unknown_previous_run_is_not_found(service):
    with pytest.raises(RunNotFoundError):
        invoke(service, VALID_DOCUMENT, previous_run_id="run-0099")


def test_previous_run_of_another_agent_is_rejected(service):
    first = service.invoke("copy-agent", InvokeRequest(input=VALID_DOCUMENT))

    with pytest.raises(InvalidRequestError):
        invoke(service, VALID_DOCUMENT, previous_run_id=first.run_id)


def test_unknown_agent_is_not_found(service):
    with pytest.raises(AgentNotFoundError):
        service.invoke("no-such-agent", InvokeRequest(input="hello"))


def test_failed_target_is_recorded_without_crashing(tmp_path):
    def handler(request):
        raise httpx2.ConnectError("refused", request=request)

    service = AdapterService(
        RunRecorder(tmp_path / "runs"), "http://down.test", transport=httpx2.MockTransport(handler)
    )

    run = service.invoke("warehouse-agent", InvokeRequest(input=VALID_DOCUMENT))

    assert run.error.type == "CONNECTION_ERROR"
    assert service.get_run(run.run_id).error.type == "CONNECTION_ERROR"


def test_object_input_is_sent_as_the_body():
    config = load_agent("warehouse-agent")

    assert build_body(config, {"message": "hi", "extra": 1}, None) == {"message": "hi", "extra": 1}
    assert build_body(config, {"message": "hi"}, "sess-9") == {
        "message": "hi",
        "sessionId": "sess-9",
    }


def test_text_input_uses_input_when_no_field_is_configured():
    config = AgentConfig.model_validate(
        {"agentId": "plain", "request": {"endpoint": "/run"}, "responseMapping": {}}
    )

    assert build_body(config, "hello", "sess-1") == {"input": "hello"}
