import subprocess

from ok_agent.tools.types import ToolSchema
from ok_agent.utils import decode_bytes


def _format_process_message(
    stdout: str | bytes | None,
    stderr: str | bytes | None,
    returncode: int | None = None,
) -> str:

    messages = []

    if stdout:
        if isinstance(stdout, bytes):
            messages.append(decode_bytes(stdout))
        elif isinstance(stdout, str):
            messages.append(stdout)

    if stderr:
        if isinstance(stderr, bytes):
            messages.append(f"<stderr>{decode_bytes(stderr)}</stderr>")
        elif isinstance(stderr, str):
            messages.append(f"<stderr>{stderr}</stderr>")

    if returncode is not None and returncode != 0:
        messages.append(f"exit code: {returncode}")

    return "\n".join(messages)


def execute_shell_command(
    cmd: str, timeout: int = 10, input: str | None = None
) -> str:
    print(f"$ {cmd}")

    try:
        result = subprocess.run(
            ["bash", "-c", cmd],
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
        return f"{cmd}: command not found"
    except OSError as e:
        return f"Failed to execute command {cmd}: {type(e).__name__} {e}"
    except ValueError as e:
        return f"Value Error {cmd}: {type(e).__name__} {e}"


shell_tool: ToolSchema = {
    "name": "shell",
    "description": "Run shell command",
    "parameters": {
        "type": "object",
        "properties": {
            "cmd": {
                "type": "string",
                "description": "shell command",
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
        "required": ["cmd"],
    },
    "function": execute_shell_command,
}
