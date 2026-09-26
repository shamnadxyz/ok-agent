from logging import getLogger

from ok_agent.ansi_sequences import BLACK_BG, RESET
from ok_agent.llama_cpp.types import FunctionTool, MessageToolCall, ToolMessage
from ok_agent.tools.registry import execute_tool
from ok_agent.tools.types import ToolRegistry, ToolSchema

logger = getLogger(__name__)


def tool_to_function_tool(tool: ToolSchema) -> FunctionTool:
    """Convert Tool to OpenAI ChatCompletionFunctionTool."""
    function: FunctionTool = {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
        },
    }

    return function


def handle_tool_call(
    registry: ToolRegistry,
    tool_call: MessageToolCall,
) -> ToolMessage:
    function = tool_call.get("function")
    arguments_json = function.get("arguments")
    name = function.get("name")

    tool_content = execute_tool(name, arguments_json, registry)

    print(f"{BLACK_BG}{tool_content}{RESET}")

    tool_message: ToolMessage = {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": tool_content,
    }

    logger.debug({**tool_message, "name": name, "arguments": arguments_json})

    return tool_message
