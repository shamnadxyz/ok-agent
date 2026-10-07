import json
from logging import getLogger
from pathlib import Path

from ok_agent.tools.types import Tool, ToolDisplayState
from ok_agent.tools.utils import handle_argument_display, is_complete
from ok_agent.utils import display_text
from ok_agent.validator import JSONSchema

logger = getLogger(__name__)
parameter_schema: JSONSchema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path for the file.",
        },
        "content": {
            "type": "string",
            "description": "Content to write",
        },
    },
    "additionalProperties": False,
    "required": ["path", "content"],
}


def write_file(path: str, content: str) -> str:
    file = Path(path)

    if file.exists():
        return f"{file.name} already exists. Cannot overwrite files. Please use edit tool"

    try:
        file.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return f"Failed to create directory '{file.name}' : {e}"

    try:
        file.write_text(content)
        return f"write success: '{path}'"
    except OSError as e:
        return f"Failed to write file '{file.name}' {type(e).__name__} {e}"
    except TypeError as e:
        return f"Type Error: {type(e).__name__} {e}"


def display_arguments(arguments: str, state: ToolDisplayState):
    """Display write tool request arguments.

    Args:
        state: Used to track the progress of printed tool argument.
        arguments: Tool request JSON string.
    """

    if is_complete("path", state) and is_complete("content", state):
        return

    if not state.get("initialized"):
        state["initialized"] = True
        display_text("Write ", "SPECIAL", end="")

    try:
        data = json.loads(arguments)
    except json.JSONDecodeError as e:
        logger.error(e)
        return

    handle_argument_display("path", state, data)
    handle_argument_display("content", state, data)


write_tool: Tool = {
    "name": "write",
    "description": "Write a new file. Parent dirs are created if missing. Cannot overwrite files.",
    "parameters": parameter_schema,
    "function": write_file,
    "display_arguments": display_arguments,
}
