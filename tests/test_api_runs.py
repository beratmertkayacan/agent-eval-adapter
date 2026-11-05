import pytest
from fastapi.testclient import TestClient

from adapter.main import app, get_service
from tests.fakes import INVALID_DOCUMENT, VALID_DOCUMENT

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_service(service):
    app.dependency_overrides[get_service] = lambda: service
    yield
    app.dependency_overrides.clear()


def invoke(body):
    return client.post("/agents/warehouse-agent/invoke", json=body)


def test_invoke_returns_raw_and_normalized_response():
    response = invoke({"input": VALID_DOCUMENT})

    assert response.status_code == 200
    body = response.json()
    assert body["runId"] == "run-0001"
    assert body["rawResponse"]["status"] == "awaiting_approval"
    assert body["normalizedResponse"]["response"]["status"] == "awaiting_approval"
    assert body["normalizedResponse"]["observability"]["requestId"] == "REQ-001"
    assert body["httpStatus"] == 200
    assert "latencyMs" in body


def test_invalid_document_returns_manual_review():
    body = invoke({"input": INVALID_DOCUMENT}).json()

    assert body["normalizedResponse"]["response"]["status"] == "manual_review"


def test_second_message_continues_the_session():
    first = invoke({"input": VALID_DOCUMENT}).json()
    second = invoke({"input": INVALID_DOCUMENT, "previousRunId": first["runId"]}).json()

    assert second["sessionId"] == first["sessionId"] == "sess-001"
    assert second["turn"] == 2
    assert second["previousRunId"] == "run-0001"

    session = client.get("/sessions/sess-001/runs").json()
    assert [run["runId"] for run in session] == ["run-0001", "run-0002"]


def test_runs_can_be_listed_and_read():
    invoke({"input": VALID_DOCUMENT})
    invoke({"input": INVALID_DOCUMENT})

    runs = client.get("/runs").json()
    run = client.get("/runs/run-0002").json()

    assert [item["runId"] for item in runs] == ["run-0001", "run-0002"]
    assert run["normalizedResponse"]["response"]["status"] == "manual_review"


def test_unknown_run_returns_404():
    response = client.get("/runs/run-0042")

    assert response.status_code == 404
    assert response.json() == {"error": "Run not found: run-0042"}


def test_unknown_agent_returns_404():
    response = client.post("/agents/no-such-agent/invoke", json={"input": "hi"})

    assert response.status_code == 404
    assert response.json() == {"error": "Agent not found: no-such-agent"}


def test_missing_input_returns_422():
    response = invoke({})

    assert response.status_code == 422
    assert response.json()["error"].startswith("Invalid request: input")


def test_unknown_previous_run_returns_404():
    response = invoke({"input": VALID_DOCUMENT, "previousRunId": "run-0099"})

    assert response.status_code == 404


def test_previous_run_of_other_agent_returns_400():
    first = client.post("/agents/copy-agent/invoke", json={"input": VALID_DOCUMENT}).json()

    response = invoke({"input": VALID_DOCUMENT, "previousRunId": first["runId"]})

    assert response.status_code == 400
    assert response.json() == {"error": "Run run-0001 belongs to agent copy-agent"}


def test_default_service_uses_settings(monkeypatch):
    monkeypatch.setenv("TARGET_AGENT_BASE_URL", "http://agent.local:9000")
    get_service.cache_clear()

    assert get_service().base_url == "http://agent.local:9000"
    get_service.cache_clear()
