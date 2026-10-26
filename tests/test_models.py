import pytest

from adapter.models import NormalizedResponse, Observability, RunRequest, RunResponse


def make_response(answer) -> NormalizedResponse:
    return NormalizedResponse(
        run_id="run-0001",
        agent_id="warehouse-agent",
        timestamp="2026-10-26T12:00:00Z",
        latency_ms=420,
        request=RunRequest(input="Invoice No: INV-1001"),
        response=RunResponse(answer=answer, status="awaiting_approval"),
        observability=Observability(),
    )


@pytest.mark.parametrize("answer", ["text", {"summary": "ok"}, ["a", "b"]])
def test_answer_can_be_string_object_or_array(answer):
    body = make_response(answer).model_dump()

    assert body["response"]["answer"] == answer


def test_normalized_response_uses_the_task_field_names():
    body = make_response("text").model_dump()

    assert list(body) == [
        "runId",
        "sessionId",
        "agentId",
        "timestamp",
        "latencyMs",
        "request",
        "response",
        "observability",
        "error",
    ]
    assert body["observability"] == {
        "toolCalls": [],
        "approval": None,
        "requestId": None,
        "auditId": None,
    }
