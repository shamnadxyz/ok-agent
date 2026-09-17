import atexit
import readline
from logging import getLogger
from pathlib import Path

from ok_agent.openai.types import ContentPartText, SystemMessage

logger = getLogger(__name__)


def setup_history():
    histfile = Path.home() / ".ok_history"
    history_length = 1000

    try:
        readline.read_history_file(histfile)
        h_len = readline.get_current_history_length()
    except FileNotFoundError:
        histfile.touch()
        h_len = 0

    def save(prev_h_len, histfile):
        new_h_len = readline.get_current_history_length()
        readline.set_history_length(history_length)
        readline.append_history_file(new_h_len - prev_h_len, histfile)

    atexit.register(save, h_len, histfile)


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
