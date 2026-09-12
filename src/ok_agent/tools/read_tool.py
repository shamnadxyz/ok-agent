from pathlib import Path

from ok_agent.ansi_sequences import BLACK_BG, BLUE_BRIGHT, RESET
from ok_agent.openai.types import FunctionTool
from ok_agent.tools.types import Tool

_read_schema: FunctionTool = {
    "type": "function",
    "function": {
        "name": "read",
        "description": "Read file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "path of the file",
                }
            },
        },
        "strict": True,
    },
}


def _read_tool(path) -> str:
    print(f"{BLACK_BG}{BLUE_BRIGHT}Read {path}{RESET}")
    if not isinstance(path, str):
        return f"path {path} should be a string"

    file = Path(path)

    try:
        if file.is_file() or file.is_symlink():
            return file.read_text()
        elif file.is_dir():
            return f"{file.name} directory contents:\n" + "\n".join(
                [dir.name for dir in file.iterdir()]
            )
        else:
            return f"read: '{file.name}' no such file or directory"
    except Exception as e:
        return f"Unable read '{file.name}' : {type(e).__name__}"


read_tool: Tool = {
    "name": _read_schema["function"]["name"],
    "schema": _read_schema,
    "tool": _read_tool,
}
