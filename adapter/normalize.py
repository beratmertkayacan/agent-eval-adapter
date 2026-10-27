from datetime import datetime, timezone
from typing import Any

from adapter.client import CallResult
from adapter.mapping import map_response
from adapter.models import (
    AgentConfig,
    NormalizedResponse,
    Observability,
    RecordedRequest,
    RunError,
    RunRecord,
    RunRequest,
    RunResponse,
)


def build_run(
    run_id: str, agent: AgentConfig, request: RecordedRequest, result: CallResult
) -> RunRecord:
    values: dict[str, Any] = {}
    error = result.error
    if error is None:
        values, missing = map_response(result.raw_response, agent.response_mapping)
        if missing:
            error = RunError(
                type="MAPPING_ERROR", message="Missing mapped field: " + ", ".join(missing)
            )

    session_id = as_text(values.get("sessionId")) or request.session_id
    timestamp = now()
    normalized = NormalizedResponse(
        run_id=run_id,
        session_id=session_id,
        agent_id=agent.agent_id,
        timestamp=timestamp,
        latency_ms=result.latency_ms,
        request=RunRequest(input=request.input),
        response=RunResponse(answer=values.get("answer"), status=as_text(values.get("status"))),
        observability=Observability(
            tool_calls=as_list(values.get("toolCalls")),
            approval=values.get("approval"),
            request_id=as_text(values.get("requestId")),
            audit_id=as_text(values.get("auditId")),
        ),
        error=error,
    )
    return RunRecord(
        run_id=run_id,
        agent_id=agent.agent_id,
        session_id=session_id,
        timestamp=timestamp,
        request=request,
        raw_response=result.raw_response,
        normalized_response=normalized,
        http_status=result.status_code,
        latency_ms=result.latency_ms,
        error=error,
    )


def as_text(value: Any) -> str | None:
    return None if value is None else str(value)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
