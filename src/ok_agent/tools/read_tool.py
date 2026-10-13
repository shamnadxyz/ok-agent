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
        },
        "offset": {
            "type": "integer",
            "description": "Offset to seek in kilobytes.",
        },
    },
    "required": ["path"],
}


def read_file(path: str, offset: int = 0) -> str:
    file = Path(path)
    max_kb = 50
    max_bytes = 51200

    if not file.exists():
        return f"'{file.name}' no such file or directory"

    if not (file.is_file() or file.is_symlink()):
        return f"reading '{file.name}' is not supported"

    try:
        file_size = file.stat().st_size

        if not file_size > max_bytes:
            return file.read_text()

        with open(file) as f:
            if offset:
                offset_bytes = offset * 1024
                f.seek(offset_bytes)

            content = "".join(f.readlines(max_bytes))
            next_content = f.readline()

            if next_content:
                return (
                    f"{content}\n[Output truncated."
                    f" file is greater than {max_kb}KB."
                    f" Use offset {offset + max_kb} to continue.]"
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
