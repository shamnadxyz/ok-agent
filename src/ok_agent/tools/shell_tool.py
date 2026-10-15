import re
import subprocess
from logging import getLogger

from ok_agent.constants import MAX_OUTPUT_CHARACTERS
from ok_agent.temporary import temporary
from ok_agent.tools.types import FormatSpec, Tool
from ok_agent.validator import JSONSchema

logger = getLogger(__name__)

parameter_schema: JSONSchema = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
        },
        "timeout": {
            "type": "number",
            "description": "command timeout (default: 10)",
        },
    },
    "required": ["command"],
}


def handle_output(
    stdout: str | bytes | None,
    stderr: str | bytes | None,
    exit_code: int | None = None,
) -> str:
    """Returns formatted process response.

    Format message with xml block if stderr is in output.
    Handle long process output saving it to a file and the info in the message.
    Adds the exit code to the end of the message.

    Args:
        stdout: content from stdout.
        stderr: content from stderr.
        exit_code: exit code of the process.
    """
    lines = []

    if stdout:
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="ignore")

        lines.append(stdout)

    if stderr:
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="ignore")

        lines.extend(
            [
                "<stderr>",
                stderr,
                "</stderr>",
            ]
        )

    message = "\n".join(lines)

    if len(message) < MAX_OUTPUT_CHARACTERS:
        if exit_code is None:
            return message
        return f"{message}\n[exit_code:{exit_code}]"

    try:
        temp_file = temporary.create_temp_file()
        temp_file.write_text(message)

        with open(temp_file) as f:
            formatted_text = f.read(MAX_OUTPUT_CHARACTERS)

            if exit_code is not None:
                formatted_text = f"{formatted_text}\n[exit_code:{exit_code}]"

            return (
                f"{formatted_text}\n[Output truncated."
                f" Full output saved to '{temp_file}'."
                f" Read with offset {f.tell()} to continue.]"
            )

    except OSError:
        logger.exception("Failed to create tempfile")

        return f"{message[:MAX_OUTPUT_CHARACTERS]}\n[Output got truncated]"


guardrails = [
    (
        r".* /( .*|$|;.*|&&.*|/+)",
        "Commands with root '/' as argument is not allowed. It is very DANGEROUS.",
    ),
    (
        r"(^| +|;)rm ",
        "rm command is forbidden. It is very DANGEROUS. Please request the user to remove the particular item.",
    ),
    (
        r"(^| +|;)ls +.*-[a-zA-Z]*R.*",
        "ls with option -R is prohibited. Please use `ls -a` to list the current directory and go from there.",
    ),
]


def check_guardrails(command: str) -> str | None:
    for regex, message in guardrails:
        if re.match(regex, command):
            return message


def execute_shell_command(command: str, timeout: int = 10) -> str:
    error_message = check_guardrails(command)

    if error_message:
        return error_message

    try:
        result = subprocess.run(
            ["sh", "-c", command],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

        return handle_output(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )

    except subprocess.TimeoutExpired as e:
        return handle_output(
            stdout=e.stdout,
            stderr=e.stderr,
        )

    except FileNotFoundError:
        return f"{command}: command not found"
    except OSError as e:
        return f"Failed to execute command {command}: {type(e).__name__} {e}"
    except ValueError as e:
        return f"Value Error {command}: {type(e).__name__} {e}"


format_spec: FormatSpec = {
    "prefix": "$ ",
    "arguments": [
        {"name": "command"},
    ],
}

shell_tool: Tool = {
    "name": "shell",
    "description": "Execute shell command.",
    "parameters": parameter_schema,
    "function": execute_shell_command,
    "format_spec": format_spec,
}
