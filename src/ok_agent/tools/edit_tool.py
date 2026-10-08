import difflib
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
            "description": "Path to the file.",
        },
        "old_text": {
            "type": "string",
            "description": "Unique text to be replaced",
        },
        "new_text": {
            "type": "string",
            "description": "Text to replace with",
        },
    },
    "required": ["path", "old_text", "new_text"],
}


def edit_file(path: str, old_text: str, new_text: str) -> str:
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


format_spec: FormatSpec = {
    "prefix": "Edit ",
    "arguments": [
        {"name": "path"},
        {"name": "old_text", "style": "ERROR"},
        {"name": "new_text", "style": "OK"},
    ],
}


edit_tool: Tool = {
    "name": "edit",
    "parameters": parameter_schema,
    "function": edit_file,
    "format_spec": format_spec,
}
