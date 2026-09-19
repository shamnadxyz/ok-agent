from pathlib import Path

from ok_agent.ansi_sequences import BLACK_BG, BLUE_BRIGHT, RESET
from ok_agent.openai.types import FunctionTool
from ok_agent.tools.types import Tool

_write_schema: FunctionTool = {
    "type": "function",
    "function": {
        "name": "write",
        "description": "Write a new file. Parent dirs are created if missing. Cannot write over exising file.",
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
        "strict": True,
    },
}


def _write(path, content) -> str:
    print(f"{BLACK_BG}{BLUE_BRIGHT}Write {path}\n{content}{RESET}")
    argument_errors = []

    if not isinstance(path, str):
        argument_errors.append(f"path: '{path}' should be a string")

    if not isinstance(content, str):
        argument_errors.append(f"content: '{content}' should be a string")

    if argument_errors:
        return "\n".join(argument_errors)

    file = Path(path)

    if file.exists():
        return f"{file.name} already exists"

    try:
        file.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return f"Unable to create directory '{file.name}' : {e}"

    try:
        file.write_text(content)

        return file.read_text()
    except Exception as e:
        return (
            f"Unable to write to file '{file.name}' : {type(e).__name__}: {e}"
        )


write_tool: Tool = {
    "name": _write_schema["function"]["name"],
    "schema": _write_schema,
    "tool": _write,
}
