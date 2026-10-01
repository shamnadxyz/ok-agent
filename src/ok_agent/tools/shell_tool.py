import subprocess

from ok_agent.tools.types import Tool
from ok_agent.validator import JSONSchema

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
        "input": {
            "type": "string",
            "description": "text sent to stdin",
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


def execute_shell_command(
    command: str, timeout: int = 10, input: str | None = None
) -> str:
    print(f"$ {command}")

    try:
        result = subprocess.run(
            ["sh", "-c", command],
            input=input,
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


shell_tool: Tool = {
    "name": "shell",
    "description": "execute shell command",
    "parameters": parameter_schema,
    "function": execute_shell_command,
}
