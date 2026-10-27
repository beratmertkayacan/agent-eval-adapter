import re
from pathlib import Path

import yaml

from adapter.models import AgentConfig

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
AGENT_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")


class AgentNotFoundError(Exception):
    pass


def load_agent(agent_id: str, agents_dir: Path = AGENTS_DIR) -> AgentConfig:
    path = agents_dir / f"{agent_id}.yaml"
    if not AGENT_ID_PATTERN.match(agent_id) or not path.is_file():
        raise AgentNotFoundError(f"Agent not found: {agent_id}")
    with path.open(encoding="utf-8") as file:
        return AgentConfig.model_validate(yaml.safe_load(file))
