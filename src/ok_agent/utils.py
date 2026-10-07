import sys
import textwrap
from logging import getLogger
from pathlib import Path
from typing import Literal

from ok_agent.ansi_sequences import (
    BOLD,
    BRIGHT_BLUE,
    BRIGHT_GRAY,
    GREEN,
    RED,
    RESET,
    YELLOW,
)
from ok_agent.llama_cpp.types import ContentPartText, SystemMessage

logger = getLogger(__name__)


def get_system_prompt() -> SystemMessage:
    agents = Path("AGENTS.md")

    system_message: list[ContentPartText] = [
        {
            "type": "text",
            "text": textwrap.dedent(f"""\
                You are a helpful coding agent. 

                cwd:"{Path.cwd()}"
                Tools will be run relative to this directory.
                """),
        },
    ]

    if agents.exists():
        try:
            content = agents.read_text()
            system_message.append({"type": "text", "text": content})
        except (OSError, ValueError):
            logger.exception("Error in reading AGENTS.md file")

    return {"role": "system", "content": system_message}


type Style = Literal["ERROR", "OK", "WARNING", "DIM", "SPECIAL"]


def display_text(
    text: str = "",
    style: Style | None = None,
    bold: bool = False,
    end: str = "\n",
):
    if end:
        text = f"{text}{end}"

    if bold:
        text = f"{BOLD}{text}{RESET}"

    if not style:
        sys.stdout.write(text)
        sys.stdout.flush()
        return

    match style:
        case "DIM":
            text = f"{BRIGHT_GRAY}{text}{RESET}"
        case "ERROR":
            text = f"{RED}{text}{RESET}"
        case "OK":
            text = f"{GREEN}{text}{RESET}"
        case "WARNING":
            text = f"{YELLOW}{text}{RESET}"
        case "SPECIAL":
            text = f"{BRIGHT_BLUE}{text}{RESET}"

    sys.stdout.write(text)
    sys.stdout.flush()
