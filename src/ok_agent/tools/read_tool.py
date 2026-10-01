import json
from pathlib import Path

from ok_agent.ansi_sequences import BLACK_BG, BLUE_BRIGHT, RESET
from ok_agent.tools.types import Tool
from ok_agent.validator import JSONSchema

parameter_schema: JSONSchema = {
    "type": "object",
    "properties": {
        "filepath": {
            "type": "string",
        }
    },
    "required": ["filepath"],
}


def read_file(filepath: str) -> str:
    print(f"{BLACK_BG}{BLUE_BRIGHT}Read {filepath}{RESET}")

    file = Path(filepath)

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


read_tool: Tool = {
    "name": "read",
    "parameters": parameter_schema,
    "function": read_file,
}
