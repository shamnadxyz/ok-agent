import re
import subprocess
from logging import getLogger

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


def _format_process_message(
    stdout: str | bytes | None,
    stderr: str | bytes | None,
    returncode: int | None = None,
) -> str:

    messages = []

    if stdout:
        if isinstance(stdout, bytes):
            messages.append(
                stdout.decode("utf-8", errors="ignore"),
            )
        elif isinstance(stdout, str):
            messages.append(stdout)

    if stderr:
        if isinstance(stderr, bytes):
            messages.extend(
                [
                    "<stderr>",
                    stderr.decode("utf-8", errors="ignore"),
                    "</stderr>",
                ]
            )
        elif isinstance(stderr, str):
            messages.append(f"<stderr>{stderr}</stderr>")

    messages.append(f"[exit_code:{returncode}]")

    return "\n".join(messages)


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
        r"(^| +|;)ls +.*-R.*",
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

        return _format_process_message(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )

    except subprocess.TimeoutExpired as e:
        return _format_process_message(
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
