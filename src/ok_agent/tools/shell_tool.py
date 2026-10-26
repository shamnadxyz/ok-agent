import subprocess
from logging import getLogger

from ok_agent.constants import MAX_OUTPUT_LINES
from ok_agent.temporary import temporary
from ok_agent.tools.types import FormatSpec, Tool
from ok_agent.validator import JSONSchema

logger = getLogger(__name__)

parameter_schema: JSONSchema = {
    'type': 'object',
    'properties': {
        'command': {
            'type': 'string',
        },
        'timeout': {
            'type': 'number',
            'description': 'command timeout in seconds (default: 10)',
        },
    },
    'required': ['command'],
}


def handle_output(
    stdout: str | bytes | None,
    stderr: str | bytes | None,
    prefix: str | None = None,
) -> str:
    """Returns formatted process response.

    Format message with xml block if stderr is in output.
    Handle long process output saving it to a file and the info in the message.
    Adds the exit code to the end of the message.

    Args:
        stdout: Content from stdout.
        stderr: Content from stderr.
        prefix: Info prepended like exit code or timeout.
    """
    message_lines = []

    if prefix:
        message_lines.append(prefix)

    if stdout:
        if isinstance(stdout, bytes):
            stdout = stdout.decode('utf-8', errors='ignore')

        message_lines.append(stdout)

    if stderr:
        if isinstance(stderr, bytes):
            stderr = stderr.decode('utf-8', errors='ignore')

        message_lines.extend(
            [
                '<stderr>',
                stderr,
                '</stderr>',
            ]
        )

    message = '\n'.join(message_lines)

    split_messages = message.splitlines()
    if len(split_messages) < MAX_OUTPUT_LINES:
        return message

    truncated_output = '\n'.join(split_messages[:MAX_OUTPUT_LINES])

    try:
        temp_file = temporary.create_temp_file()
        temp_file.write_text(message, encoding='utf-8')

        return (
            'Output got truncated'
            f"\n- Full output saved to '{temp_file}'"
            f'\n- Read with offset {MAX_OUTPUT_LINES + 1} to continue'
            '\nOutput:'
            f'\n{truncated_output}'
        )

    except OSError:
        logger.exception('Failed to create tempfile')

        return f'Output got truncated\nOutput:\n{truncated_output}'


def execute_shell_command(command: str, timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            ['sh', '-c', command],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

        return handle_output(
            stdout=result.stdout,
            stderr=result.stderr,
            prefix=f'Exit code: {result.returncode}',
        )

    except subprocess.TimeoutExpired as e:
        return handle_output(
            stdout=e.stdout,
            stderr=e.stderr,
            prefix=f'Timeout expired: {timeout}',
        )

    except FileNotFoundError:
        return f'{command}: command not found'
    except OSError as e:
        return f'Failed to execute command {command}: {type(e).__name__} {e}'
    except ValueError as e:
        return f'Value Error {command}: {type(e).__name__} {e}'


format_spec: FormatSpec = {
    'prefix': '$ ',
    'arguments': [
        {'name': 'command'},
    ],
}

shell_tool: Tool = {
    'name': 'shell',
    'description': 'Execute shell command.',
    'parameters': parameter_schema,
    'function': execute_shell_command,
    'format_spec': format_spec,
}
