import json
from typing import Any, Literal

from adapter.models import RunRecord

ExportFormat = Literal["json", "jsonl"]


def to_dataset(runs: list[RunRecord]) -> list[dict[str, Any]]:
    rows = []
    for run in runs:
        normalized = run.normalized_response
        rows.append(
            {
                "input": run.request.input,
                "output": normalized.response.answer,
                "metadata": {
                    "runId": run.run_id,
                    "agentId": run.agent_id,
                    "sessionId": run.session_id,
                    "turn": run.turn,
                    "status": normalized.response.status,
                    "toolCalls": normalized.observability.tool_calls,
                    "latencyMs": run.latency_ms,
                    "replayOf": run.replay_of,
                    "error": run.error.type if run.error else None,
                },
            }
        )
    return rows


def export_runs(runs: list[RunRecord], fmt: ExportFormat = "json") -> str:
    rows = to_dataset(runs)
    if fmt == "jsonl":
        return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    return json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
