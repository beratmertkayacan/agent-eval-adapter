import json
import re
from pathlib import Path
from typing import Iterable

from adapter.models import RunRecord
from adapter.redaction import redact

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
RUN_ID_PATTERN = re.compile(r"^run-(\d{4,})$")


class RunNotFoundError(Exception):
    pass


class RunRecorder:
    def __init__(self, runs_dir: Path = RUNS_DIR):
        self.runs_dir = runs_dir

    def next_run_id(self) -> str:
        numbers = [int(RUN_ID_PATTERN.match(path.stem).group(1)) for path in self._files()]
        return f"run-{max(numbers, default=0) + 1:04d}"

    def save(self, record: RunRecord, extra_fields: Iterable[str] = ()) -> RunRecord:
        data = redact(record.model_dump(), extra_fields)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        path = self.runs_dir / f"{record.run_id}.json"
        with path.open("x", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        return RunRecord.model_validate(data)

    def get(self, run_id: str) -> RunRecord:
        path = self.runs_dir / f"{run_id}.json"
        if not RUN_ID_PATTERN.match(run_id) or not path.is_file():
            raise RunNotFoundError(f"Run not found: {run_id}")
        return self._read(path)

    def list_runs(self) -> list[RunRecord]:
        return [self._read(path) for path in self._files()]

    def _files(self) -> list[Path]:
        if not self.runs_dir.is_dir():
            return []
        files = [
            path for path in self.runs_dir.glob("run-*.json") if RUN_ID_PATTERN.match(path.stem)
        ]
        return sorted(files, key=lambda path: int(path.stem.split("-")[1]))

    def _read(self, path: Path) -> RunRecord:
        return RunRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
