import json
from logging import getLogger

from ok_agent.llama_cpp.types import Content
from ok_agent.tools.types import Tool
from ok_agent.validator import validate_object as validate_tool
from ok_agent.validator.validator import ValidationError

logger = getLogger(__name__)


class ToolNotFoundError(Exception):
    def __init__(self, name):
        self.name = name

        super().__init__(f"Tool not found: '{self.name}'")


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools = {tool.name: tool for tool in tools}

    @property
    def tools(self) -> list[Tool]:
        """List of available Tool objects."""
        return [tool for tool in self._tools.values()]

    def execute_tool(self, name: str, arguments: str) -> Content:
        tool = self._tools.get(name)

        if tool is None:
            message = f"tool: '{name}' not found"
            logger.error(message)
            return message

        function = tool.function

        try:
            args = json.loads(arguments)
            validate_tool(args, tool.parameters)
            return function(**args)

        except json.JSONDecodeError as e:
            logger.exception('JSON decode error')
            return f'Invalid arguments JSON: {e}'

        except ValidationError as e:
            return str(e)

        except TypeError as e:
            return f'Inappropriate argument type: {e}'

        except Exception as e:  # noqa: BLE001
            return f'Tool call failed: {type(e).__name__}: {e}'

    def get_tool(self, name: str) -> Tool:
        """Returns Tool object with the given name.

        Args:
            name: Name of the tool.

        Raises:
            ToolNotFoundError: If the tool is not found.
        """
        tool = self._tools.get(name)

        if tool is None:
            raise ToolNotFoundError(name=name)

        return tool

    def get_tools(self) -> list[str]:
        """Returns a list of available tool names."""
        return [tool for tool in self._tools]
