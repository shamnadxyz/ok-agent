import os
from logging import getLogger
from pathlib import Path
from typing import TypedDict

logger = getLogger(__name__)


class Config(TypedDict):
    model: str
    api_base_url: str
    api_key: str | None
    history_length: int
    logs_path: str


def _get_base_url():
    return os.getenv(
        "OPENAI_BASE_URL", "http://localhost:9931/v1"
    ).removesuffix("/")


def _get_logs_path():
    home = Path.home()
    return home / ".local/state/ok-agent"


def get_config() -> Config:
    return {
        "model": os.getenv("MODEL", "qwen3.6-35b-a3b"),
        "api_base_url": _get_base_url(),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "history_length": 1000,
        "logs_path": _get_logs_path(),
    }
