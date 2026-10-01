import json
import subprocess

from ok_agent.tools.types import Tool



def execute_shell_command(
    cmd: str, timeout: int = 10, input: str | None = None
) -> str:
    print(f"$ {cmd}")

    try:
        result = subprocess.run(
            ["sh", "-c", cmd],
            input=input,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return json.dumps(
            {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            },
            separators=(":", ","),
        )

    except subprocess.TimeoutExpired as e:
        return json.dumps(
            {"stdout": e.stdout, "stderr": e.stderr, "timeout": True},
            separators=(":", ","),
        )

    except FileNotFoundError:
        return f"{cmd}: command not found"
    except OSError as e:
        return f"Failed to execute command {cmd}: {type(e).__name__} {e}"
    except ValueError as e:
        return f"Value Error {cmd}: {type(e).__name__} {e}"


shell_tool: Tool = {
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
