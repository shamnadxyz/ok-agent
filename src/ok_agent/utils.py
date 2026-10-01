from pathlib import Path

from ok_agent.config import logger
from ok_agent.constants import AGENT_PROMPT
from ok_agent.llama_cpp.types import ContentPartText, SystemMessage


def get_system_prompt() -> SystemMessage:
    agents = Path("AGENTS.md")

    system_message: list[ContentPartText] = [
        {
            "type": "text",
            "text": AGENT_PROMPT,
        },
    ]

    if agents.exists():
        try:
            content = agents.read_text()
            system_message.append({"type": "text", "text": content})
        except (OSError, ValueError):
            logger.exception("Error in reading AGENTS.md file")

    return {"role": "system", "content": system_message}
