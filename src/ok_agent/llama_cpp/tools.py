from logging import getLogger

from ok_agent.llama_cpp.types import FunctionTool, MessageToolCall, ToolMessage
from ok_agent.tools import Tool, ToolRegistry
from ok_agent.utils import display_text

logger = getLogger(__name__)


def tool_to_function_tool(tool: Tool) -> FunctionTool:
    """Convert Tool to OpenAI ChatCompletionFunctionTool."""
    function: FunctionTool = {
        "type": "function",
        "function": {
            "name": tool["name"],
            "parameters": tool["parameters"],
        },
    }

    if "description" in tool:
        function["function"]["description"] = tool["description"]

    return function


def handle_tool_calls(
    tool_registry: ToolRegistry,
    tool_calls: list[MessageToolCall],
) -> list[ToolMessage]:

    tool_messages: list[ToolMessage] = []

    for tool_call in tool_calls:
        function = tool_call.get("function")
        arguments_json = function.get("arguments")
        name = function.get("name")

        tool_content = tool_registry.execute_tool(name, arguments_json)
        display_text(tool_content)

        tool_call_id = tool_call["id"]

        tool_message: ToolMessage = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": tool_content,
        }

        tool_messages.append(tool_message)

        logger.debug(
            {**tool_message, "name": name, "arguments": arguments_json}
        )

    return tool_messages
