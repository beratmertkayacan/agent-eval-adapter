import json

import pytest

import export
import replay
from adapter.models import InvokeRequest
from tests.fakes import VALID_DOCUMENT


@pytest.fixture(autouse=True)
def use_fake_service(monkeypatch, service):
    monkeypatch.setattr(replay, "get_service", lambda: service)
    monkeypatch.setattr(export, "get_service", lambda: service)


def test_replay_script_creates_a_new_run(service, capsys):
    service.invoke("warehouse-agent", InvokeRequest(input=VALID_DOCUMENT))

    code = replay.main(["run-0001"])

    assert code == 0
    assert (
        "run-0002 replays run-0001 (status: awaiting_approval, error: none)"
        in capsys.readouterr().out
    )


def test_replay_script_reports_unknown_run(capsys):
    assert replay.main(["run-0099"]) == 1
    assert "Run not found: run-0099" in capsys.readouterr().out


def test_export_script_writes_jsonl(service, tmp_path, capsys):
    service.invoke("warehouse-agent", InvokeRequest(input=VALID_DOCUMENT))
    output = tmp_path / "dataset.jsonl"

    code = export.main(["--format", "jsonl", "--output", str(output)])

    assert code == 0
    assert json.loads(output.read_text().strip())["metadata"]["runId"] == "run-0001"
    assert "Exported 1 runs" in capsys.readouterr().out


def test_export_script_default_path(service, tmp_path, monkeypatch):
    monkeypatch.setattr(export, "EXPORTS_DIR", tmp_path / "exports")

    export.main([])

    assert json.loads((tmp_path / "exports" / "dataset.json").read_text()) == []
