import difflib
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
        "old_text": {
            "type": "string",
            "description": "unique text to be replaced",
        },
        "new_text": {
            "type": "string",
            "description": "text to replace with",
        },
    },
    "required": ["filepath", "old_text", "new_text"],
}


def edit_file(filepath: str, old_text: str, new_text: str) -> str:
    print(f"{BLACK_BG}{BLUE_BRIGHT}Edit {filepath}{RESET}")

    file = Path(filepath)

    if not file.exists():
        return f"File '{file.name}' does not exists"

    file_content = file.read_text()

    if old_text == new_text:
        return "old_text and new_text cannot be the same"

    count = file_content.count(old_text)

    if count == 0:
        return "old_text does not have a match in the file"

    if count > 1:
        return "old_text must be unique"

    updated_content = file_content.replace(old_text, new_text, count=1)

    try:
        file.write_text(updated_content, encoding="utf-8")
        return "".join(
            difflib.unified_diff(
                file_content.splitlines(keepends=True),
                updated_content.splitlines(keepends=True),
            )
        )

    except OSError as e:
        return (
            f"Failed to edit the file '{file.name}' : {type(e).__name__}: {e}"
        )
    except TypeError as e:
        return f"Type Error: {type(e).__name__}: {e}"


edit_tool: Tool = {
    "name": "edit",
    "parameters": parameter_schema,
    "function": edit_file,
}
