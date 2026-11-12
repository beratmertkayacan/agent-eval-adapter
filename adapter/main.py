from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from adapter.agent_config import AgentNotFoundError
from adapter.config import load_settings
from adapter.export import ExportFormat, export_runs
from adapter.models import InvokeRequest, RunRecord
from adapter.recorder import RunNotFoundError, RunRecorder
from adapter.service import AdapterService, InvalidRequestError

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR.parent / ".env")

app = FastAPI(title="Agent Evaluation Adapter", version="0.1.0")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


@lru_cache
def get_service() -> AdapterService:
    return AdapterService(RunRecorder(), load_settings().target_agent_base_url)


@app.exception_handler(AgentNotFoundError)
@app.exception_handler(RunNotFoundError)
async def handle_not_found(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": str(error)})


@app.exception_handler(InvalidRequestError)
async def handle_invalid(request: Request, error: InvalidRequestError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(error)})


@app.exception_handler(RequestValidationError)
async def handle_invalid_body(request: Request, error: RequestValidationError) -> JSONResponse:
    problems = []
    for item in error.errors():
        field = ".".join(str(part) for part in item["loc"][1:]) or "body"
        problems.append(f"{field}: {item['msg']}")
    return JSONResponse(
        status_code=422, content={"error": "Invalid request: " + "; ".join(problems)}
    )


@app.get("/", include_in_schema=False)
def playground() -> FileResponse:
    return FileResponse(APP_DIR / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/agents")
def list_agents(service: AdapterService = Depends(get_service)) -> list[str]:
    return service.list_agents()


@app.post("/agents/{agent_id}/invoke")
def invoke_agent(
    agent_id: str, request: InvokeRequest, service: AdapterService = Depends(get_service)
) -> RunRecord:
    return service.invoke(agent_id, request)


@app.get("/runs")
def list_runs(service: AdapterService = Depends(get_service)) -> list[RunRecord]:
    return service.list_runs()


@app.get("/runs/{run_id}")
def get_run(run_id: str, service: AdapterService = Depends(get_service)) -> RunRecord:
    return service.get_run(run_id)


@app.get("/sessions/{session_id}/runs")
def session_runs(
    session_id: str, service: AdapterService = Depends(get_service)
) -> list[RunRecord]:
    return service.session_runs(session_id)


@app.post("/runs/{run_id}/replay")
def replay_run(run_id: str, service: AdapterService = Depends(get_service)) -> RunRecord:
    return service.replay(run_id)


@app.get("/export")
def export(
    format: ExportFormat = "json", service: AdapterService = Depends(get_service)
) -> PlainTextResponse:
    media_type = "application/x-ndjson" if format == "jsonl" else "application/json"
    return PlainTextResponse(export_runs(service.list_runs(), format), media_type=media_type)
