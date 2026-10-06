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


def handle_tool_call(
    tool_registry: ToolRegistry,
    tool_call: MessageToolCall,
) -> ToolMessage:
    function = tool_call.get("function")
    arguments_json = function.get("arguments")
    name = function.get("name")

    tool_content = tool_registry.execute_tool(name, arguments_json)
    display_text(tool_content)

    tool_message: ToolMessage = {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": tool_content,
    }

    logger.debug({**tool_message, "name": name, "arguments": arguments_json})

    return tool_message
