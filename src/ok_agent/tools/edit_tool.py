import difflib
import json
from logging import getLogger
from pathlib import Path

from ok_agent.ansi_sequences import (
    BRIGHT_BLUE,
    GREEN,
    RED,
    RESET,
)
from ok_agent.tools.types import Tool, ToolDisplayState
from ok_agent.tools.utils import handle_argument_display, is_complete
from ok_agent.validator import JSONSchema

logger = getLogger(__name__)

parameter_schema: JSONSchema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file.",
        },
        "old_text": {
            "type": "string",
            "description": "Unique text to be replaced",
        },
        "new_text": {
            "type": "string",
            "description": "Text to replace with",
        },
    },
    "required": ["path", "old_text", "new_text"],
}


def edit_file(path: str, old_text: str, new_text: str) -> str:
    file = Path(path)

    if not file.exists():
        return f"File '{file.name}' does not exists"

    file_content = file.read_text()

    if old_text == new_text:
        return "old_text and new_text cannot be the same"

    count = file_content.count(old_text)

    if count == 0:
        return "old_text does not have a match in the file"

    if count > 1:
        return "old_text must be unique"

    updated_content = file_content.replace(old_text, new_text, count=1)

    try:
        file.write_text(updated_content, encoding="utf-8")
        return "".join(
            difflib.unified_diff(
                file_content.splitlines(keepends=True),
                updated_content.splitlines(keepends=True),
            )
        )

    except OSError as e:
        return (
            f"Failed to edit the file '{file.name}' : {type(e).__name__}: {e}"
        )
    except TypeError as e:
        return f"Type Error: {type(e).__name__}: {e}"


def display_arguments(arguments: str, state: ToolDisplayState):
    """Display edit tool request arguments.

    Args:
        state: Used to track the progress of printed tool arguments.
        arguments: Tool request JSON string.
    """

    if (
        is_complete("path", state)
        and is_complete("old_text", state)
        and is_complete("new_text", state)
    ):
        return

    if not state.get("initialized"):
        state["initialized"] = True
        print(f"{BRIGHT_BLUE}Edit {RESET}", end="", flush=True)

    try:
        data = json.loads(arguments)
    except json.JSONDecodeError as e:
        logger.error(e)
        return

    handle_argument_display(name="path", state=state, data=data)
    handle_argument_display(
        name="old_text", prefix=RED, suffix=RESET, state=state, data=data
    )
    handle_argument_display(
        name="new_text", prefix=GREEN, suffix=RESET, state=state, data=data
    )


edit_tool: Tool = {
    "name": "edit",
    "parameters": parameter_schema,
    "function": edit_file,
    "display_arguments": display_arguments,
}
