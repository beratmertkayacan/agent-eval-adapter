import json

import httpx2
import pytest
from fastapi.testclient import TestClient

from adapter.models import InvokeRequest
from adapter.recorder import RunRecorder
from adapter.redaction import REDACTED
from adapter.service import AdapterService, InvalidRequestError
from mock_agent.main import app as mock_app

mock_client = TestClient(mock_app)


def forward_to_mock_agent(request: httpx2.Request) -> httpx2.Response:
    """Send the adapter request to the mock agent app, without any network."""
    response = mock_client.post(request.url.path, json=json.loads(request.content))
    return httpx2.Response(response.status_code, json=response.json())


@pytest.fixture
def service(tmp_path, monkeypatch) -> AdapterService:
    monkeypatch.setenv("MOCK_AGENT_BASE_URL", "http://mock.test")
    return AdapterService(
        RunRecorder(tmp_path / "runs"),
        "http://warehouse.test",
        transport=httpx2.MockTransport(forward_to_mock_agent),
    )


def invoke(service, text, previous_run_id=None):
    return service.invoke("mock-agent", InvokeRequest(input=text, previous_run_id=previous_run_id))


def test_mock_agent_has_its_own_response_shape():
    body = mock_client.post("/run", json={"query": "hello there"}).json()

    assert body["result"]["message"] == {"text": "You said: hello there", "wordCount": 2}
    assert body["result"]["state"] == "completed"
    assert body["conversation"]["id"].startswith("conv-")


def test_second_agent_works_through_configuration_only(service):
    run = invoke(service, "hello there")
    normalized = run.normalized_response

    assert run.request.body == {"query": "hello there"}
    assert run.error is None
    assert normalized.agent_id == "mock-agent"
    assert normalized.response.answer == {"text": "You said: hello there", "wordCount": 2}
    assert normalized.response.status == "completed"
    assert normalized.observability.tool_calls == [{"tool": "count_words"}]
    assert normalized.observability.audit_id.startswith("trace-")
    assert normalized.session_id.startswith("conv-")


def test_second_agent_reuses_its_session(service):
    first = invoke(service, "hello")
    second = invoke(service, "again", previous_run_id=first.run_id)

    assert second.request.body == {"query": "again", "conversationId": first.session_id}
    assert second.session_id == first.session_id
    assert second.turn == 2


def test_token_from_the_agent_is_not_stored(service):
    run = invoke(service, "hello")

    text = (service.recorder.runs_dir / f"{run.run_id}.json").read_text()
    assert "mock-token-123" not in text
    assert run.raw_response["debug"]["token"] == REDACTED


def test_missing_base_url_variable_is_reported(service, monkeypatch):
    monkeypatch.delenv("MOCK_AGENT_BASE_URL")

    with pytest.raises(InvalidRequestError, match="MOCK_AGENT_BASE_URL is not set"):
        invoke(service, "hello")
