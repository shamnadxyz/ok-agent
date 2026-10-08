from logging import getLogger
from pathlib import Path

from ok_agent.tools.types import FormatSpec, Tool
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


format_spec: FormatSpec = {
    "prefix": "Write ",
    "arguments": [
        {"name": "path"},
        {"name": "content"},
    ],
}

write_tool: Tool = {
    "name": "write",
    "description": "Write a new file. Parent dirs are created if missing. Cannot overwrite files.",
    "parameters": parameter_schema,
    "function": write_file,
    "format_spec": format_spec,
}
