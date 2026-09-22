from pathlib import Path

from ok_agent.config import logger
from ok_agent.openai.types import ContentPartText, SystemMessage


def decode_bytes(input: bytes) -> str:
    return input.decode("utf-8", errors="ignore")


def get_system_prompt() -> SystemMessage:
    agents = Path("AGENTS.md")

    system_message: list[ContentPartText] = [
        {
            "type": "text",
            "text": "You are a coding agent inside the Ok agent harness. Your focus is on minimalism in everything.",
        },
    ]

    if agents.exists():
        try:
            content = agents.read_text()
            system_message.append({"type": "text", "text": content})
        except (OSError, ValueError):
            logger.exception("Error in reading AGENTS.md file")

    return {"role": "system", "content": system_message}
