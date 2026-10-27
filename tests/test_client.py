import json

import httpx2
import pytest

from adapter.client import call_agent
from adapter.models import AgentConfig

CONFIG = AgentConfig.model_validate(
    {
        "agentId": "test-agent",
        "request": {"endpoint": "/agent/chat", "timeoutSeconds": 5},
        "responseMapping": {"answer": "answer"},
    }
)
BASE_URL = "http://agent.test"


def fake_agent(handler):
    return httpx2.MockTransport(handler)


def test_successful_call_returns_json_and_status():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json={"answer": "ok", "status": "awaiting_approval"})

    result = call_agent(CONFIG, BASE_URL + "/", {"message": "hi"}, fake_agent(handler))

    assert seen == {"url": "http://agent.test/agent/chat", "body": {"message": "hi"}}
    assert result.status_code == 200
    assert result.raw_response == {"answer": "ok", "status": "awaiting_approval"}
    assert result.error is None
    assert result.latency_ms >= 0


def test_get_request_sends_body_as_query_parameters():
    config = CONFIG.model_copy(
        update={"request": CONFIG.request.model_copy(update={"method": "GET"})}
    )

    def handler(request):
        assert request.method == "GET"
        return httpx2.Response(200, json={"query": dict(request.url.params)})

    result = call_agent(config, BASE_URL, {"q": "stock"}, fake_agent(handler))

    assert result.raw_response == {"query": {"q": "stock"}}


@pytest.mark.parametrize("code", [400, 404, 500, 503])
def test_http_errors_are_recorded_with_the_body(code):
    def handler(request):
        return httpx2.Response(code, json={"error": "something failed"})

    result = call_agent(CONFIG, BASE_URL, {}, fake_agent(handler))

    assert result.status_code == code
    assert result.raw_response == {"error": "something failed"}
    assert result.error.type == "HTTP_ERROR"
    assert result.error.status_code == code
    assert result.error.message == f"Target agent returned HTTP {code}"


def test_http_error_with_text_body_keeps_the_text():
    def handler(request):
        return httpx2.Response(502, text="Bad Gateway")

    result = call_agent(CONFIG, BASE_URL, {}, fake_agent(handler))

    assert result.raw_response == "Bad Gateway"
    assert result.error.type == "HTTP_ERROR"


def test_invalid_json_is_recorded_as_text():
    def handler(request):
        return httpx2.Response(200, text="<html>not json</html>")

    result = call_agent(CONFIG, BASE_URL, {}, fake_agent(handler))

    assert result.status_code == 200
    assert result.raw_response == "<html>not json</html>"
    assert result.error.type == "INVALID_JSON"


def test_timeout_is_recorded():
    def handler(request):
        raise httpx2.ReadTimeout("timed out", request=request)

    result = call_agent(CONFIG, BASE_URL, {}, fake_agent(handler))

    assert result.status_code is None
    assert result.raw_response is None
    assert result.error.type == "TIMEOUT"
    assert result.error.message == "Target agent did not answer within 5 seconds"


def test_connection_error_is_recorded():
    def handler(request):
        raise httpx2.ConnectError("connection refused", request=request)

    result = call_agent(CONFIG, BASE_URL, {}, fake_agent(handler))

    assert result.status_code is None
    assert result.error.type == "CONNECTION_ERROR"
    assert result.error.message == "Could not connect to the target agent"
