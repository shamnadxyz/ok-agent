from logging import getLogger
from pathlib import Path

from ok_agent.constants import MAX_OUTPUT_CHARACTERS
from ok_agent.tools.types import FormatSpec, Tool
from ok_agent.validator import JSONSchema

logger = getLogger(__name__)

parameter_schema: JSONSchema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
        },
        "offset": {
            "type": "integer",
            "description": "Content position start.",
        },
        "max_chars": {
            "type": "integer",
            "description": "Maximum character limit.",
        },
    },
    "required": ["path"],
}


def read_file(
    path: str,
    offset: int = 0,
    max_chars: int = MAX_OUTPUT_CHARACTERS,
) -> str:
    """Read file content.

    Truncates file content greater than MAX_OUTPUT_CHARACTERS.

    Args:
        path: path to the file.
        offset: read position.
        max_chars: Maximum character limit.
    """
    file = Path(path)

    if not file.exists():
        return f"'{file.name}' no such file or directory"

    if not (file.is_file() or file.is_symlink()):
        return f"reading '{file.name}' is not supported"

    try:
        with open(file) as f:
            if offset:
                f.seek(offset)

            content = f.read(max_chars)

            next_content = f.read(1)

            if next_content:
                end = f.tell() - 1
                return (
                    f"{content}\n[Showing {offset}-{end}."
                    f" Read with offset {f.tell()} to continue.]"
                )

            return content

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
