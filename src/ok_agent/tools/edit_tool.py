import difflib
from pathlib import Path

from ok_agent.ansi_sequences import BLACK_BG, BLUE_BRIGHT, RESET
from ok_agent.openai.types import FunctionTool
from ok_agent.tools.types import Tool

_edit_schema: FunctionTool = {
    "type": "function",
    "function": {
        "name": "edit",
        "description": "Edit an existing file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "path of the file to edit",
                },
                "old_text": {
                    "type": "string",
                    "description": "exact unique text to be replace",
                },
                "new_text": {
                    "type": "string",
                    "description": "text to replace with",
                },
            },
        },
        "strict": True,
    },
}


def _edit(path, old_text, new_text) -> str:
    print(f"{BLACK_BG}{BLUE_BRIGHT}Edit {path}{RESET}")
    argument_errors = []

    if not isinstance(path, str):
        argument_errors.append(f"path: '{path}' should be a string")

    if not isinstance(old_text, str):
        argument_errors.append(f"old_text: '{old_text}' should be a string")

    if not isinstance(new_text, str):
        argument_errors.append(f"new_text: '{new_text}' should be a string")

    if argument_errors:
        return "\n".join(argument_errors)

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
        file.write_text(updated_content)
        return "".join(
            difflib.unified_diff(
                file_content.splitlines(keepends=True),
                updated_content.splitlines(keepends=True),
            )
        )

    except Exception as e:
        return f"Unable edit the file '{file.name}' : {type(e).__name__}: {e}"


edit_tool: Tool = {
    "name": _edit_schema["function"]["name"],
    "schema": _edit_schema,
    "tool": _edit,
}
