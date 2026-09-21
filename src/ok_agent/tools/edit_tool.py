import difflib
from pathlib import Path

from ok_agent.ansi_sequences import BLACK_BG, BLUE_BRIGHT, RESET
from ok_agent.tools.types import ToolSchema


def edit_file(path: str, old_text: str, new_text: str) -> str:
    print(f"{BLACK_BG}{BLUE_BRIGHT}Edit {path}{RESET}")

    file = Path(path)

    if not file.exists():
        return f"File '{file.name}' does not exists"

    file_content = file.read_text()

    if old_text == new_text:
        return "old_text and new_text cannot be the same"

    count = file_content.count(old_text)

    if count == 0:
        return "old_text does not have a match in the file"

    if count > 1:
        return "old_text have more that one match in the file, it should be unique"

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


edit_tool: ToolSchema = {
    "name": "edit",
    "description": "Edit a file",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "path of file",
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
    },
    "strict": True,
    "function": edit_file,
}
