import os
from typing import TypedDict


class Config(TypedDict):
    model: str
    api_base_url: str
    api_key: str | None
    logs_path: str


def _get_base_url():
    return os.getenv(
        "OPENAI_BASE_URL", "http://localhost:9931/v1"
    ).removesuffix("/")


def get_config() -> Config:
    return {
        "model": os.getenv("MODEL", "qwen3.6-35b-a3b"),
        "api_base_url": _get_base_url(),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "logs_path": "/var/tmp/ok-agent",
    }
