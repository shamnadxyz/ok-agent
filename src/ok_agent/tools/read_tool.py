import json
from logging import getLogger
from pathlib import Path

from ok_agent.ansi_sequences import BRIGHT_BLUE, RESET
from ok_agent.tools.types import Tool, ToolDisplayState
from ok_agent.tools.utils import handle_argument_display, is_complete
from ok_agent.validator import JSONSchema

logger = getLogger(__name__)

parameter_schema: JSONSchema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
        }
    },
    "required": ["path"],
}


def read_file(path: str) -> str:
    file = Path(path)

    try:
        if file.is_file() or file.is_symlink():
            return file.read_text()
        elif file.is_dir():
            return json.dumps(
                {
                    "type": "DIR",
                    "content": [item.name for item in file.iterdir()],
                },
                separators=(",", ":"),
            )
        elif file.exists():
            return f"reading '{file.name}' is not supported"
        else:
            return f"'{file.name}' no such file or directory"
    except OSError as e:
        return f"Failed to read '{file.name}' {type(e).__name__} {e}"
    except TypeError as e:
        return f"Type Error '{file.name}' {type(e).__name__} {e}"


def display_arguments(arguments: str, state: ToolDisplayState):
    """Display read tool request arguments.

    Args:
        state: Used to track the progress of printed tool arguments.
        arguments: Tool request JSON string.
    """

    if is_complete("path", state):
        return

    if not state.get("initialized"):
        print(f"{BRIGHT_BLUE}Read {RESET}", end="", flush=True)
        state["initialized"] = True

    try:
        data = json.loads(arguments)
    except json.JSONDecodeError as e:
        logger.error(e)
        return

    handle_argument_display(name="path", state=state, data=data)


read_tool: Tool = {
    "name": "read",
    "parameters": parameter_schema,
    "function": read_file,
    "display_arguments": display_arguments,
}
