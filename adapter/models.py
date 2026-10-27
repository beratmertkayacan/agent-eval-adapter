from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MappedField = Literal[
    "answer", "status", "sessionId", "toolCalls", "approval", "requestId", "auditId"
]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        serialize_by_alias=True,
    )


class RequestConfig(CamelModel):
    endpoint: str
    method: Literal["GET", "POST"] = "POST"
    input_field: str | None = None
    session_field: str | None = None
    timeout_seconds: float = 30


class AgentConfig(CamelModel):
    agent_id: str
    request: RequestConfig
    response_mapping: dict[MappedField, str]
    redact_fields: list[str] = []


class RunRequest(CamelModel):
    input: Any


class RunResponse(CamelModel):
    answer: Any = None
    status: str | None = None


class Observability(CamelModel):
    tool_calls: list[Any] = []
    approval: Any = None
    request_id: str | None = None
    audit_id: str | None = None


class RunError(CamelModel):
    type: str
    message: str
    status_code: int | None = None


class NormalizedResponse(CamelModel):
    run_id: str
    session_id: str | None = None
    agent_id: str
    timestamp: str
    latency_ms: int
    request: RunRequest
    response: RunResponse
    observability: Observability
    error: RunError | None = None


class RecordedRequest(CamelModel):
    input: Any
    session_id: str | None = None
    body: dict[str, Any]


class RunRecord(CamelModel):
    run_id: str
    agent_id: str
    session_id: str | None = None
    timestamp: str
    request: RecordedRequest
    raw_response: Any = None
    normalized_response: NormalizedResponse
    http_status: int | None = None
    latency_ms: int
    error: RunError | None = None
