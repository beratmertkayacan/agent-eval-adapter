import time
from dataclasses import dataclass
from typing import Any

import httpx2

from adapter.models import AgentConfig, RunError


@dataclass
class CallResult:
    status_code: int | None
    raw_response: Any
    latency_ms: int
    error: RunError | None


def call_agent(
    config: AgentConfig,
    base_url: str,
    body: dict[str, Any],
    transport: httpx2.BaseTransport | None = None,
) -> CallResult:
    request = config.request
    url = base_url.rstrip("/") + request.endpoint
    payload = {"json": body} if request.method == "POST" else {"params": body}
    start = time.perf_counter()

    try:
        with httpx2.Client(transport=transport, timeout=request.timeout_seconds) as client:
            response = client.request(request.method, url, **payload)
    except httpx2.TimeoutException:
        message = f"Target agent did not answer within {request.timeout_seconds:g} seconds"
        return CallResult(None, None, elapsed_ms(start), RunError(type="TIMEOUT", message=message))
    except httpx2.RequestError:
        message = "Could not connect to the target agent"
        error = RunError(type="CONNECTION_ERROR", message=message)
        return CallResult(None, None, elapsed_ms(start), error)

    latency = elapsed_ms(start)
    raw, is_json = read_body(response)
    error = None
    if response.is_error:
        error = RunError(
            type="HTTP_ERROR",
            status_code=response.status_code,
            message=f"Target agent returned HTTP {response.status_code}",
        )
    elif not is_json:
        error = RunError(type="INVALID_JSON", message="Target agent did not return valid JSON")
    return CallResult(response.status_code, raw, latency, error)


def read_body(response: httpx2.Response) -> tuple[Any, bool]:
    try:
        return response.json(), True
    except ValueError:
        return response.text, False


def elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)
