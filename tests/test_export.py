import json

import httpx2

from adapter.export import export_runs, to_dataset
from adapter.models import InvokeRequest
from tests.fakes import INVALID_DOCUMENT, VALID_DOCUMENT


def make_runs(service):
    first = service.invoke("warehouse-agent", InvokeRequest(input=VALID_DOCUMENT))
    service.invoke(
        "warehouse-agent", InvokeRequest(input=INVALID_DOCUMENT, previous_run_id=first.run_id)
    )
    return service.list_runs()


def test_dataset_row_has_input_output_and_metadata(service):
    rows = to_dataset(make_runs(service))

    assert rows[0]["input"] == VALID_DOCUMENT
    assert rows[0]["output"] == "Human approval is required before shipment release."
    assert rows[0]["metadata"]["sessionId"] == "sess-001"
    assert rows[0]["metadata"]["status"] == "awaiting_approval"
    assert rows[1]["metadata"]["status"] == "manual_review"
    assert rows[1]["metadata"]["turn"] == 2
    assert rows[1]["metadata"]["error"] is None


def test_json_export_is_one_array(service):
    text = export_runs(make_runs(service), "json")

    data = json.loads(text)
    assert isinstance(data, list) and len(data) == 2


def test_jsonl_export_has_one_object_per_line(service):
    text = export_runs(make_runs(service), "jsonl")

    lines = text.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[1])["metadata"]["runId"] == "run-0002"


def test_failed_run_is_exported_with_its_error_type(service):
    def handler(request):
        return httpx2.Response(500, text="boom")

    service.transport = httpx2.MockTransport(handler)
    service.invoke("warehouse-agent", InvokeRequest(input=VALID_DOCUMENT))

    row = to_dataset(service.list_runs())[0]
    assert row["output"] is None
    assert row["metadata"]["error"] == "HTTP_ERROR"


def test_empty_export():
    assert export_runs([], "json") == "[]\n"
    assert export_runs([], "jsonl") == ""
