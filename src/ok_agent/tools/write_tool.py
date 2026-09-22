from pathlib import Path

from ok_agent.ansi_sequences import BLACK_BG, BLUE_BRIGHT, RESET
from ok_agent.tools.types import ToolSchema


def write_file(path: str, content: str) -> str:
    print(f"{BLACK_BG}{BLUE_BRIGHT}Write {path}\n{content}{RESET}")

    file = Path(path)

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


write_tool: ToolSchema = {
    "name": "write",
    "description": "Write a new file. Parent dirs are created if missing. Cannot write over existing file.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "path for the file",
            },
            "content": {
                "type": "string",
                "description": "content to write",
            },
        },
    },
    "function": write_file,
}
