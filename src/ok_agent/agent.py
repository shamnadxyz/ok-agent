from typing import cast

from ok_agent.constants import AGENT_PROMPT
from ok_agent.llama_cpp.completions import completion
from ok_agent.llama_cpp.tools import handle_tool_call, tool_to_function_tool
from ok_agent.llama_cpp.types import (
    AssistantMessage,
    Content,
    Message,
    SystemMessage,
)
from ok_agent.tools.registry import Tool, ToolRegistry


class NoResponseError(Exception):
    def __init__(self, message: str = "The model did not produce any reponse"):
        self.message = message


def agent(
    query: str,
    tools: list[Tool],
    model: str,
    messages: list[Message],
    system_prompt: Content = AGENT_PROMPT,
) -> str:

    tool_registry = ToolRegistry(tools)
    function_tools = [tool_to_function_tool(tool) for tool in tools]

    message = None

    if not messages:
        system_message: SystemMessage = {
            "role": "system",
            "content": system_prompt,
        }
        messages.append(system_message)

    user_message: Message = {"role": "user", "content": query}
    messages.append(user_message)

    while response := completion(
        model=model,
        messages=messages,
        tools=function_tools,
    ):
        assistant_response = response["message"]
        finish_reason = response["finish_reason"]

        # Store content response for returning as the final response
        if "content" in assistant_response:
            message = assistant_response["content"]

        if (
            "content" in assistant_response
            or "tool_calls" in assistant_response
        ):
            messages.append(cast(AssistantMessage, assistant_response))
        else:
            raise NoResponseError()

        if "tool_calls" in assistant_response:
            tool_results = [
                handle_tool_call(tool_registry, tool_call)
                for tool_call in assistant_response["tool_calls"]
            ]

            messages.extend(tool_results)

        match finish_reason:
            case "length":
                print("Token generation limit exceeded.")
                break
            case "stop":
                break
            case "tool_calls":
                pass
    if message is None:
        raise NoResponseError()

    return message
