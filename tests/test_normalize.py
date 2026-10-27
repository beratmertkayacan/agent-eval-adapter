from adapter.agent_config import load_agent
from adapter.client import CallResult
from adapter.models import AgentConfig, RecordedRequest, RunError
from adapter.normalize import build_run

WAREHOUSE = load_agent("warehouse-agent")
REQUEST = RecordedRequest(input="Invoice No: INV-1001", body={"message": "Invoice No: INV-1001"})
VALID_RESPONSE = {
    "sessionId": "sess-001",
    "answer": "Human approval is required before shipment release.",
    "status": "awaiting_approval",
    "toolCalls": [{"name": "get_order"}, {"name": "submit_for_human_approval"}],
    "approval": {"id": "APR-001", "status": "pending"},
    "requestId": "REQ-001",
}


def ok(raw) -> CallResult:
    return CallResult(status_code=200, raw_response=raw, latency_ms=420, error=None)


def test_warehouse_response_is_normalized():
    run = build_run("run-0001", WAREHOUSE, REQUEST, ok(VALID_RESPONSE))
    normalized = run.normalized_response

    assert normalized.run_id == "run-0001"
    assert normalized.session_id == "sess-001"
    assert normalized.agent_id == "warehouse-agent"
    assert normalized.latency_ms == 420
    assert normalized.timestamp.endswith("Z")
    assert normalized.request.input == "Invoice No: INV-1001"
    assert normalized.response.status == "awaiting_approval"
    assert normalized.observability.tool_calls == VALID_RESPONSE["toolCalls"]
    assert normalized.observability.approval == {"id": "APR-001", "status": "pending"}
    assert normalized.observability.request_id == "REQ-001"
    assert normalized.observability.audit_id is None
    assert normalized.error is None


def test_raw_response_and_http_details_are_kept():
    run = build_run("run-0001", WAREHOUSE, REQUEST, ok(VALID_RESPONSE))

    assert run.raw_response == VALID_RESPONSE
    assert run.http_status == 200
    assert run.latency_ms == 420
    assert run.session_id == "sess-001"
    assert run.request == REQUEST


def test_manual_review_with_null_approval_is_not_an_error():
    raw = {**VALID_RESPONSE, "status": "manual_review", "approval": None, "requestId": None}

    run = build_run("run-0001", WAREHOUSE, REQUEST, ok(raw))

    assert run.error is None
    assert run.normalized_response.response.status == "manual_review"
    assert run.normalized_response.observability.approval is None


def test_missing_mapped_field_is_a_mapping_error():
    raw = {key: value for key, value in VALID_RESPONSE.items() if key != "status"}

    run = build_run("run-0001", WAREHOUSE, REQUEST, ok(raw))

    assert run.error.type == "MAPPING_ERROR"
    assert run.error.message == "Missing mapped field: status"
    assert run.normalized_response.error == run.error
    assert run.normalized_response.response.answer == VALID_RESPONSE["answer"]


def test_another_agent_shape_is_normalized_through_config():
    agent = AgentConfig.model_validate(
        {
            "agentId": "other-agent",
            "request": {"endpoint": "/run"},
            "responseMapping": {
                "answer": "result.message",
                "status": "result.state",
                "toolCalls": "actions",
            },
        }
    )
    raw = {"result": {"message": {"text": "Done"}, "state": "completed"}, "actions": "search"}
    request = RecordedRequest(input="hi", session_id="s-9", body={"input": "hi"})

    run = build_run("run-0002", agent, request, ok(raw))

    assert run.normalized_response.response.answer == {"text": "Done"}
    assert run.normalized_response.response.status == "completed"
    assert run.normalized_response.observability.tool_calls == ["search"]
    assert run.normalized_response.session_id == "s-9"


def test_failed_call_is_not_mapped():
    error = RunError(type="HTTP_ERROR", status_code=500, message="Target agent returned HTTP 500")
    result = CallResult(
        status_code=500, raw_response={"detail": "boom"}, latency_ms=12, error=error
    )

    run = build_run("run-0001", WAREHOUSE, REQUEST, result)

    assert run.error == error
    assert run.raw_response == {"detail": "boom"}
    assert run.normalized_response.response.status is None
    assert run.normalized_response.observability.tool_calls == []


def test_non_text_ids_are_stored_as_text():
    raw = {**VALID_RESPONSE, "requestId": 42}

    run = build_run("run-0001", WAREHOUSE, REQUEST, ok(raw))

    assert run.normalized_response.observability.request_id == "42"
