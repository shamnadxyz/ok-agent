import json
from logging import getLogger

from ok_agent.tools.edit_tool import edit_tool
from ok_agent.tools.read_tool import read_tool
from ok_agent.tools.shell_tool import shell_tool
from ok_agent.tools.types import (
    Tool,
    ToolRegistry,
)
from ok_agent.tools.write_tool import write_tool
from ok_agent.validator import validate_object as validate_tool
from ok_agent.validator.validator import ValidationError

logger = getLogger(__name__)


def execute_tool(name: str, arguments: str, registry: ToolRegistry) -> str:
    tool = registry.get(name)

    if tool is None:
        message = f"tool: '{name}' not found"
        logger.error(message)
        return message

    function = tool.get("function")

    try:
        args = json.loads(arguments)
        validate_tool(args, tool["parameters"])
        return function(**args)

    except json.JSONDecodeError as e:
        logger.exception("JSON decode error")
        return f"Invalid arguments JSON: {e}"

    except ValidationError as e:
        return e.message

    except TypeError as e:
        return f"Inappropriate argument type: {e}"

    except Exception as e:  # noqa: BLE001
        return f"Tool call failed: {type(e).__name__}: {e}"


def get_tools() -> list[Tool]:
    return [read_tool, write_tool, shell_tool, edit_tool]


def create_registry(tools: list[Tool]) -> ToolRegistry:
    return {tool["name"]: tool for tool in tools}
