import os
from logging import getLogger
from pathlib import Path
from typing import TypedDict

logger = getLogger(__name__)


class Config(TypedDict):
    api_base_url: str
    api_key: str | None
    history_length: int
    state_dir: Path
    data_dir: Path


def _get_base_url():
    return os.getenv(
        "OPENAI_BASE_URL", "http://localhost:9931/v1"
    ).removesuffix("/")


def _get_data_dir():
    home = Path.home()
    return home / ".local/share/ok-agent"


def _get_state_dir() -> Path:
    home = Path.home()
    return home / ".local/state/ok-agent"


def get_config() -> Config:
    return {
        "api_base_url": _get_base_url(),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "history_length": 1000,
        "state_dir": _get_state_dir(),
        "data_dir": _get_data_dir(),
    }
