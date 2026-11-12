import pytest
from fastapi.testclient import TestClient

from adapter.agent_config import list_agent_ids
from adapter.main import app, get_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_service(service):
    app.dependency_overrides[get_service] = lambda: service
    yield
    app.dependency_overrides.clear()


def test_playground_page_is_served():
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Agent Evaluation Adapter" in response.text


@pytest.mark.parametrize(
    "element_id",
    ["agent", "input", "send", "raw", "normalized", "latency", "session-id", "run-id", "replay"],
)
def test_page_has_the_parts_from_the_task(element_id):
    assert f'id="{element_id}"' in client.get("/").text
    assert 'id="history"' in client.get("/").text


def test_playground_script_is_served():
    response = client.get("/static/app.js")

    assert response.status_code == 200
    for path in ["/agents", "/invoke", "/replay", "/runs"]:
        assert path in response.text


def test_playground_is_not_part_of_the_api_schema():
    paths = client.get("/openapi.json").json()["paths"]

    assert "/" not in paths


def test_agents_endpoint_lists_the_configured_agents():
    response = client.get("/agents")

    assert response.status_code == 200
    assert response.json() == ["copy-agent", "warehouse-agent"]


def test_real_agents_folder_has_both_example_agents():
    assert list_agent_ids() == ["mock-agent", "warehouse-agent"]


def test_files_with_invalid_names_are_not_listed(tmp_path):
    (tmp_path / "good-agent.yaml").write_text("agentId: good-agent")
    (tmp_path / "Bad Agent.yaml").write_text("agentId: bad")
    (tmp_path / "notes.txt").write_text("not an agent")

    assert list_agent_ids(tmp_path) == ["good-agent"]
