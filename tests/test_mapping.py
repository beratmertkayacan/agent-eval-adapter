from adapter.mapping import MISSING, get_path, map_response

WAREHOUSE_MAPPING = {
    "answer": "answer",
    "status": "status",
    "sessionId": "sessionId",
    "toolCalls": "toolCalls",
    "approval": "approval",
    "requestId": "requestId",
}


def test_flat_fields_are_mapped():
    raw = {
        "sessionId": "sess-001",
        "answer": "Human approval is required.",
        "status": "awaiting_approval",
        "toolCalls": [{"name": "get_order"}],
        "approval": {"id": "APR-001", "status": "pending"},
        "requestId": "REQ-001",
    }

    values, missing = map_response(raw, WAREHOUSE_MAPPING)

    assert missing == []
    assert values["status"] == "awaiting_approval"
    assert values["approval"] == {"id": "APR-001", "status": "pending"}


def test_nested_paths_are_mapped():
    raw = {"result": {"message": "Done", "state": "ok"}, "actions": ["search"]}
    mapping = {"answer": "result.message", "status": "result.state", "toolCalls": "actions"}

    values, missing = map_response(raw, mapping)

    assert values == {"answer": "Done", "status": "ok", "toolCalls": ["search"]}
    assert missing == []


def test_list_index_in_path():
    raw = {"choices": [{"message": {"content": "Hello"}}]}

    assert get_path(raw, "choices.0.message.content") == "Hello"
    assert get_path(raw, "choices.5.message") is MISSING


def test_missing_fields_are_reported_and_set_to_none():
    raw = {"answer": "text"}

    values, missing = map_response(raw, {"answer": "answer", "status": "result.state"})

    assert values == {"answer": "text", "status": None}
    assert missing == ["status"]


def test_null_value_is_not_missing():
    values, missing = map_response({"approval": None}, {"approval": "approval"})

    assert values == {"approval": None}
    assert missing == []


def test_path_through_a_non_object_is_missing():
    assert get_path({"answer": "text"}, "answer.value") is MISSING
    assert get_path("not json object", "answer") is MISSING
