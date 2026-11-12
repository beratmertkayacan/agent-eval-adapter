"""A second example agent with a different API shape than the Warehouse Agent.

It has no LLM. It only exists to show that the adapter can connect a new
agent through a YAML file, without any change in the adapter code.

Run it with: uvicorn mock_agent.main:app --port 8002
"""

from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock Support Agent", version="0.1.0")


class RunRequest(BaseModel):
    query: str
    conversationId: str | None = None


@app.post("/run")
def run(request: RunRequest) -> dict:
    words = request.query.split()
    return {
        "result": {
            "message": {"text": f"You said: {request.query}", "wordCount": len(words)},
            "state": "completed" if words else "needs_input",
        },
        "actions": [{"tool": "count_words"}],
        "conversation": {"id": request.conversationId or f"conv-{uuid4().hex[:8]}"},
        "trace": {"id": f"trace-{uuid4().hex[:8]}"},
        "debug": {"token": "mock-token-123"},
    }
