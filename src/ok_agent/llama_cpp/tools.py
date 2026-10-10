from logging import getLogger

from ok_agent.config import get_config
from ok_agent.llama_cpp.types import FunctionTool, MessageToolCall, ToolMessage
from ok_agent.tools import Tool, ToolRegistry
from ok_agent.tools.utils import format_tool_call
from ok_agent.utils import clear_lines_above, display_text

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

    config = get_config()

    tool_messages: list[ToolMessage] = []
    tool_calls_map: dict[str, MessageToolCall] = {}

    tool_texts: list[str] = []
    newlines = 0

    for tool_call in tool_calls:
        function = tool_call.get("function")
        arguments_json = function.get("arguments")
        name = function.get("name")

        tool_content = tool_registry.execute_tool(name, arguments_json)

        tool_call_id = tool_call["id"]

        tool_message: ToolMessage = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": tool_content,
        }

        tool_messages.append(tool_message)

        tool_calls_map[tool_call_id] = tool_call

        logger.debug(
            {**tool_message, "name": name, "arguments": arguments_json}
        )

        formatted_text = format_tool_call(
            tool_call=tool_call,
            state={"initialized": False, "argument_states": {}},
            is_final=True,
        )

        if formatted_text is not None:
            newlines += len(formatted_text.splitlines())
            tool_texts.append(f"{formatted_text}{tool_content}")

    if config.show_tool_result:
        clear_lines_above(count=newlines)

        for text in tool_texts:
            display_text(text)

    return tool_messages
