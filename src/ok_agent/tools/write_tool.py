from pathlib import Path

from ok_agent.ansi_sequences import BLACK_BG, BLUE_BRIGHT, RESET
from ok_agent.tools.types import Tool
from ok_agent.validator import JSONSchema

parameter_schema: JSONSchema = {
    "type": "object",
    "properties": {
        "filepath": {
            "type": "string",
        },
        "content": {
            "type": "string",
        },
    },
    "required": ["filepath", "content"],
}


def write_file(filepath: str, content: str) -> str:
    print(f"{BLACK_BG}{BLUE_BRIGHT}Write {filepath}\n{content}{RESET}")

    file = Path(filepath)

    if file.exists():
        return f"{file.name} already exists"

    try:
        file.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return f"Failed to create directory '{file.name}' : {e}"

    try:
        file.write_text(content)

        return file.read_text()
    except OSError as e:
        return f"Failed to write file '{file.name}' {type(e).__name__} {e}"
    except TypeError as e:
        return f"Type Error: {type(e).__name__} {e}"


write_tool: Tool = {
    "name": "write",
    "description": "Write a new file. Parent dirs are created if missing. Cannot overwrite an existing file.",
    "parameters": parameter_schema,
    "function": write_file,
}
