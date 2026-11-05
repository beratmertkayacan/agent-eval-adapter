import json

import pytest
from fastapi.testclient import TestClient

from adapter.main import app, get_service
from tests.fakes import VALID_DOCUMENT

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_service(service):
    app.dependency_overrides[get_service] = lambda: service
    yield
    app.dependency_overrides.clear()


def invoke():
    return client.post("/agents/warehouse-agent/invoke", json={"input": VALID_DOCUMENT}).json()


def test_replay_endpoint_creates_a_new_run():
    original = invoke()

    response = client.post(f"/runs/{original['runId']}/replay")

    assert response.status_code == 200
    assert response.json()["runId"] == "run-0002"
    assert response.json()["replayOf"] == "run-0001"


def test_replay_of_unknown_run_returns_404():
    response = client.post("/runs/run-0099/replay")

    assert response.status_code == 404
    assert response.json() == {"error": "Run not found: run-0099"}


def test_export_json_is_the_default():
    invoke()

    response = client.get("/export")

    assert response.headers["content-type"].startswith("application/json")
    assert json.loads(response.text)[0]["metadata"]["runId"] == "run-0001"


def test_export_jsonl():
    invoke()
    invoke()

    response = client.get("/export", params={"format": "jsonl"})

    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert len(response.text.strip().split("\n")) == 2


def test_unknown_export_format_returns_422():
    response = client.get("/export", params={"format": "csv"})

    assert response.status_code == 422
