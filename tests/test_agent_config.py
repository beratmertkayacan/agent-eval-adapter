import pytest
from pydantic import ValidationError

from adapter.agent_config import AgentNotFoundError, load_agent


def test_warehouse_agent_config_loads():
    config = load_agent("warehouse-agent")

    assert config.agent_id == "warehouse-agent"
    assert config.request.endpoint == "/agent/chat"
    assert config.request.method == "POST"
    assert config.request.input_field == "message"
    assert config.request.session_field == "sessionId"
    assert config.response_mapping["status"] == "status"


def test_unknown_agent_raises_not_found():
    with pytest.raises(AgentNotFoundError):
        load_agent("no-such-agent")


@pytest.mark.parametrize("agent_id", ["../secrets", "Warehouse", "agent/x"])
def test_invalid_agent_id_is_not_read(agent_id):
    with pytest.raises(AgentNotFoundError):
        load_agent(agent_id)


def test_config_from_another_folder(tmp_path):
    (tmp_path / "other-agent.yaml").write_text(
        "agentId: other-agent\n"
        "request:\n"
        "  endpoint: /run\n"
        "responseMapping:\n"
        "  answer: result.message\n"
        "  status: result.state\n"
        "  toolCalls: actions\n"
    )

    config = load_agent("other-agent", agents_dir=tmp_path)

    assert config.request.method == "POST"
    assert config.request.timeout_seconds == 30
    assert config.response_mapping == {
        "answer": "result.message",
        "status": "result.state",
        "toolCalls": "actions",
    }


def test_unknown_mapping_field_is_rejected(tmp_path):
    (tmp_path / "typo-agent.yaml").write_text(
        "agentId: typo-agent\nrequest:\n  endpoint: /run\nresponseMapping:\n  anwser: answer\n"
    )

    with pytest.raises(ValidationError):
        load_agent("typo-agent", agents_dir=tmp_path)
