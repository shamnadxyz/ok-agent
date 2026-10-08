import json
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


format_spec: FormatSpec = {
    "prefix": "Read ",
    "arguments": [
        {"name": "path"},
    ],
}

read_tool: Tool = {
    "name": "read",
    "parameters": parameter_schema,
    "function": read_file,
    "format_spec": format_spec,
}
