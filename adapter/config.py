import os
from dataclasses import dataclass

DEFAULT_TARGET_URL = "http://127.0.0.1:8000"
DEFAULT_PORT = 8001


@dataclass(frozen=True)
class Settings:
    target_agent_base_url: str
    port: int


def load_settings() -> Settings:
    return Settings(
        target_agent_base_url=os.getenv("TARGET_AGENT_BASE_URL") or DEFAULT_TARGET_URL,
        port=int(os.getenv("PORT") or DEFAULT_PORT),
    )
