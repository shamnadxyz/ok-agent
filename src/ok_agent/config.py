import os
from typing import TypedDict


class Config(TypedDict):
    model: str
    api_base_url: str
    logs_path: str


def get_config() -> Config:
    return {
        "model": os.getenv("MODEL", "qwen3.6-35b-a3b"),
        "api_base_url": os.getenv("LLM_BASE_URL", "http://localhost:9931"),
        "logs_path": "/var/tmp/ok-agent",
    }
