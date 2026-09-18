import os
from logging import getLogger
from pathlib import Path
from typing import TypedDict

from ok_agent.openai.types import ContentPartText, SystemMessage

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


def get_config() -> Config:
    return {
        "model": os.getenv("MODEL", "qwen3.6-35b-a3b"),
        "api_base_url": _get_base_url(),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "history_length": 1000,
        "logs_path": "/var/tmp/ok-agent",
    }


def get_system_prompt() -> SystemMessage:
    agents = Path("AGENTS.md")

    system_message: list[ContentPartText] = [
        {
            "type": "text",
            "text": "You are a coding agent inside the Ok agent harness. Your focus is on minimalism in everything.",
        },
        {
            "type": "text",
            "text": "Currently the harness doesn't support markdown, responding in markdown is strictly forbidden, use only plain text format.",
        },
    ]

    if agents.exists():
        try:
            content = agents.read_text()
            system_message.append({"type": "text", "text": content})
        except (OSError, ValueError):
            logger.exception("Error in reading AGENTS.md file")

    return {"role": "system", "content": system_message}
