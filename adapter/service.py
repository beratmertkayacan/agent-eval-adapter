import os
from pathlib import Path
from typing import Any

import httpx2

from adapter.agent_config import AGENTS_DIR, list_agent_ids, load_agent
from adapter.client import call_agent
from adapter.models import AgentConfig, InvokeRequest, RecordedRequest, RunRecord
from adapter.normalize import build_run
from adapter.recorder import RunRecorder


class InvalidRequestError(Exception):
    pass


def build_body(agent: AgentConfig, user_input: Any, session_id: str | None) -> dict[str, Any]:
    if isinstance(user_input, dict):
        body = dict(user_input)
    else:
        body = {agent.request.input_field or "input": user_input}
    if session_id and agent.request.session_field:
        body[agent.request.session_field] = session_id
    return body


class AdapterService:
    def __init__(
        self,
        recorder: RunRecorder,
        base_url: str,
        agents_dir: Path = AGENTS_DIR,
        transport: httpx2.BaseTransport | None = None,
    ):
        self.recorder = recorder
        self.base_url = base_url
        self.agents_dir = agents_dir
        self.transport = transport

    def invoke(self, agent_id: str, request: InvokeRequest) -> RunRecord:
        agent = load_agent(agent_id, self.agents_dir)
        previous = None
        if request.previous_run_id:
            previous = self.recorder.get(request.previous_run_id)
            if previous.agent_id != agent.agent_id:
                raise InvalidRequestError(
                    f"Run {previous.run_id} belongs to agent {previous.agent_id}"
                )

        session_id = previous.session_id if previous else None
        recorded = RecordedRequest(
            input=request.input,
            session_id=session_id,
            body=build_body(agent, request.input, session_id),
        )
        run = self._call(agent, recorded)
        if previous:
            run.previous_run_id = previous.run_id
            run.turn = previous.turn + 1
        return self.recorder.save(run, agent.redact_fields)

    def replay(self, run_id: str) -> RunRecord:
        original = self.recorder.get(run_id)
        agent = load_agent(original.agent_id, self.agents_dir)
        run = self._call(agent, original.request)
        run.replay_of = original.run_id
        run.previous_run_id = original.previous_run_id
        run.turn = original.turn
        return self.recorder.save(run, agent.redact_fields)

    def _call(self, agent: AgentConfig, recorded: RecordedRequest) -> RunRecord:
        result = call_agent(agent, self._base_url(agent), recorded.body, self.transport)
        return build_run(self.recorder.next_run_id(), agent, recorded, result)

    def _base_url(self, agent: AgentConfig) -> str:
        if agent.base_url_env == "TARGET_AGENT_BASE_URL":
            return self.base_url
        base_url = os.getenv(agent.base_url_env)
        if not base_url:
            raise InvalidRequestError(f"Environment variable {agent.base_url_env} is not set")
        return base_url

    def list_agents(self) -> list[str]:
        return list_agent_ids(self.agents_dir)

    def list_runs(self) -> list[RunRecord]:
        return self.recorder.list_runs()

    def get_run(self, run_id: str) -> RunRecord:
        return self.recorder.get(run_id)

    def session_runs(self, session_id: str) -> list[RunRecord]:
        return [run for run in self.recorder.list_runs() if run.session_id == session_id]
