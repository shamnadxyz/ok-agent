import json
from logging import getLogger

from ok_agent.tools.edit_tool import edit_tool
from ok_agent.tools.read_tool import read_tool
from ok_agent.tools.shell_tool import shell_tool
from ok_agent.tools.types import Tool
from ok_agent.tools.write_tool import write_tool
from ok_agent.validator import validate_object as validate_tool
from ok_agent.validator.validator import ValidationError

logger = getLogger(__name__)


class ToolNotFoundError(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"Tool not found: '{self.name}'"


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools = {tool["name"]: tool for tool in tools}

    def execute_tool(self, name: str, arguments: str) -> str:
        tool = self._tools.get(name)

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

    def get_tools(self, tool_names: list[str] | None = None) -> list[Tool]:
        """Returns available tools.

        Args:
            tools: name of tools to return

        Raises:
            ToolNotFoundError: if specified tool not found
        """
        if tool_names is None:
            return [tool for _, tool in self._tools.items()]

        tools = []
        for tool in tool_names:
            if tool in self._tools:
                tools.append(self._tools[tool])
            else:
                raise ToolNotFoundError(name=tool)

        return tools


TOOL_REGISTRY = ToolRegistry(
    tools=[read_tool, write_tool, edit_tool, shell_tool]
)
