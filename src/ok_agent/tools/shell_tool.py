import subprocess

from ok_agent.openai.types import FunctionTool
from ok_agent.tools.types import Tool
from ok_agent.utils import decode_bytes

_shell_schema: FunctionTool = {
    "type": "function",
    "function": {
        "name": "shell",
        "description": "Run shell command",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "shell command to run",
                },
                "timeout": {
                    "type": "number",
                    "description": "command timeout (default: 10)",
                },
                "input": {
                    "type": ["string", "null"],
                    "description": "Input send to the command's stdin",
                },
            },
        },
        "strict": True,
    },
}


def _build_process_message(
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


def execute_shell_command(cmd, timeout=10, input=None) -> str:
    print(f"$ {cmd}")

    argument_errors = []

    if not isinstance(cmd, str):
        argument_errors.append(f"cmd: '{cmd}' should be a string")

    if not isinstance(timeout, int):
        argument_errors.append(f"timeout: '{timeout}' should be a number")

    if not isinstance(input, str) and input is not None:
        argument_errors.append(f"input: '{input}' should be a string or null")

    if argument_errors:
        return "\n".join(argument_errors)

    try:
        result = subprocess.run(
            ["bash", "-c", cmd],
            input=input,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return _build_process_message(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )

    except subprocess.TimeoutExpired as e:
        return _build_process_message(
            stdout=e.stdout,
            stderr=e.stderr,
        )

    except Exception as e:
        return f"Unable to execute command {cmd}: {type(e).__name__}\n{e}"


shell_tool: Tool = {
    "name": _shell_schema["function"]["name"],
    "schema": _shell_schema,
    "tool": execute_shell_command,
}
