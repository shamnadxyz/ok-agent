import base64
from pathlib import Path

from ok_agent.constants import MAX_OUTPUT_LINES
from ok_agent.llama_cpp.types import Content
from ok_agent.tools.types import FormatSpec, Tool
from ok_agent.validator import JSONSchema

parameter_schema: JSONSchema = {
    'type': 'object',
    'properties': {
        'path': {
            'type': 'string',
        },
        'offset': {
            'type': 'integer',
            'description': 'Line to start reading.',
            'minimum': 0,
        },
        'lines': {
            'type': 'integer',
            'description': 'Number of lines to read.',
            'minimum': 1,
        },
    },
    'required': ['path'],
}


def _is_supported_image(file: Path) -> str | None:
    """Returns the mime type if file is supported image."""
    if not file.is_file() or not file.exists():
        return None

    IMAGE_SIGNATURES = {
        'image/png': b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a',
        'image/jpeg': b'\xff\xd8\xff',
        'image/webp': b'RIFF',
    }

    with open(file, 'br') as f:
        header = f.read(16)
        for mime, signature in IMAGE_SIGNATURES.items():
            if header.startswith(signature):
                return mime


def read_file(
    path: str,
    offset: int = 0,
    lines: int = MAX_OUTPUT_LINES,
) -> Content:
    """Read file content.

    Truncates file content greater than MAX_OUTPUT_LINES.

    Args:
        path: Path to the file.
        offset: Line to start reading.
        lines: Number of lines to read.
    """
    file = Path(path)

    if not file.exists():
        return f"'{file.name}' no such file or directory"

    if not (file.is_file() or file.is_symlink()):
        return f"reading '{file.name}' is not supported"

    try:
        with open(file) as f:
            contents = []

            if offset > 1:
                for _ in range(offset - 1):
                    f.readline()

            for count, line in enumerate(f, start=1):
                contents.append(line)
                if count == lines:
                    break

            next_content = f.read(1)

            content = ''.join(contents)

            line_count = len(contents)

            start_line = max(1, offset)
            end_line = line_count + max(0, offset - 1)

            if next_content:
                return (
                    f'Showing lines: {start_line}-{end_line}'
                    f'\nContinue with offset: {end_line + 1}'
                    f'\nContent:'
                    f'\n{content}'
                )

            return content

    except UnicodeDecodeError as e:
        if mime_type := _is_supported_image(file):
            image_bytes = file.read_bytes()
            data = base64.b64encode(image_bytes).decode('ascii')
            return [
                {
                    'type': 'image_url',
                    'image_url': {'url': f'data:{mime_type};base64,{data}'},
                }
            ]

        return f"Failed to read '{file.name}' {type(e).__name__} {e}"

    except OSError as e:
        return f"Failed to read '{file.name}' {type(e).__name__} {e}"
    except TypeError as e:
        return f"Type Error '{file.name}' {type(e).__name__} {e}"


format_spec: FormatSpec = {
    'prefix': 'Read ',
    'arguments': [
        {'name': 'path'},
    ],
}

read_tool: Tool = {
    'name': 'read',
    'description': 'Read files. Supported image formats: png, jpeg, and webp.',
    'parameters': parameter_schema,
    'function': read_file,
    'format_spec': format_spec,
}
