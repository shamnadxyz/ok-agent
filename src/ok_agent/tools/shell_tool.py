import subprocess

from ok_agent.openai.types import FunctionTool
from ok_agent.tools.types import Tool


def _build_process_message(stdout: str, stderr: str, returncode: int) -> str:
    if stderr:
        message = f"<stdout>{stdout}</stdout>\n<stderr>\n{stderr}</stderr>"
    else:
        message = stdout

    if returncode != 0:
        message += f"\nExited with non-zero exit code: {returncode}"

    return message


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
                    "description": "bash command to run",
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


def execute_shell_command(cmd, input=None) -> str:
    print(f"$ {cmd}")

    argument_errors = []

    if not isinstance(cmd, str):
        argument_errors.append(f"cmd: '{cmd}' should be a string")

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
            check=False,
        )
        return _build_process_message(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )
    except Exception as e:
        return f"Unable to execute command {cmd}: {type(e).__name__}\n{e}"


shell_tool: Tool = {
    "name": _shell_schema["function"]["name"],
    "schema": _shell_schema,
    "tool": execute_shell_command,
}
