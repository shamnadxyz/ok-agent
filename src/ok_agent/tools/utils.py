import json
from logging import getLogger

from ok_agent.ansi_sequences import BLACK_BG, RESET
from ok_agent.openai.types import (
    FunctionTool,
    Message,
    MessageToolCall,
)
from ok_agent.tools.types import Tool, Tools

logger = getLogger(__name__)


def get_tools_schema(
    selected_tools: list[Tool],
) -> tuple[list[FunctionTool], Tools]:

    tool_schemas: list[FunctionTool] = [
        tool["schema"] for tool in selected_tools
    ]
    tools: Tools = {tool["name"]: tool["tool"] for tool in selected_tools}

    return (tool_schemas, tools)


def execute_tool(tools: Tools, tool_call: MessageToolCall) -> str:
    function = tool_call.get("function")
    arguments_json = function.get("arguments")
    name = function.get("name")

    tool = tools.get(name)

    if tool is None:
        message = f"tool: '{name}' not found"
        logger.error(message)
        return message

    try:
        arguments = json.loads(arguments_json)
        result = tool(**arguments)
        print(f"{BLACK_BG}{result}{RESET}")
        return result
    except json.JSONDecodeError as e:
        logger.exception("parse_tool_call: Invalid JSON arguments")
        return f"parse_tool_call: Invalid JSON arguments: {e}"
    except Exception as e:
        return f"Tool call error: {type(e).__name__}: {e}"


def handle_tool_calls(
    tools: Tools,
    tool_calls: list[MessageToolCall],
) -> list[Message]:

    tool_results: list[Message] = [
        {
            "role": "tool",
            "tool_call_id": tool_call.get("id"),
            "content": execute_tool(tools, tool_call),
        }
        for tool_call in tool_calls
    ]

    logger.debug(f"Tool results: {tool_results}")

    return tool_results
