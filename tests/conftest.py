import httpx2
import pytest

from adapter.agent_config import AGENTS_DIR
from adapter.recorder import RunRecorder
from adapter.service import AdapterService
from tests.fakes import fake_warehouse_agent


@pytest.fixture
def agents_dir(tmp_path):
    """The real warehouse config plus a copy under another agent ID."""
    folder = tmp_path / "agents"
    folder.mkdir()
    text = (AGENTS_DIR / "warehouse-agent.yaml").read_text()
    (folder / "warehouse-agent.yaml").write_text(text)
    (folder / "copy-agent.yaml").write_text(
        text.replace("agentId: warehouse-agent", "agentId: copy-agent")
    )
    return folder


@pytest.fixture
def service(tmp_path, agents_dir) -> AdapterService:
    return AdapterService(
        RunRecorder(tmp_path / "runs"),
        "http://warehouse.test",
        agents_dir=agents_dir,
        transport=httpx2.MockTransport(fake_warehouse_agent),
    )
