from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR.parent / ".env")

app = FastAPI(title="Agent Evaluation Adapter", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
