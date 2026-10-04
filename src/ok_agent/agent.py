from typing import cast
from urllib.error import URLError

from ok_agent.constants import AGENT_PROMPT
from ok_agent.llama_cpp.completions import (
    CompletionError,
    NoFinishReasonError,
    completion,
)
from ok_agent.llama_cpp.tools import handle_tool_call, tool_to_function_tool
from ok_agent.llama_cpp.types import (
    AssistantMessage,
    Content,
    Message,
    SystemMessage,
)
from ok_agent.tools.registry import Tool, ToolRegistry


class NoResponseError(Exception):
    """Raises when the agent fails to produce a response."""

    def __init__(self, message: str = "The model failed to produce a response"):
        self.message = message

    def __str__(self):
        return self.message


class TurnLimitExceededError(Exception):
    """Raises when the maximum number of turns are exceeded.

    Attributes:
        agent_response: The agent response from the last turn.
    """

    def __init__(
        self,
        message: str = "The maximum number of turns exceeded",
        agent_response: str | None = None,
    ):
        self.agent_response = agent_response
        self.message = message
        super().__init__(message)

    def __str__(self):
        return self.message


def agent(
    query: str,
    tools: list[Tool],
    model: str,
    messages: list[Message],
    system_prompt: Content = AGENT_PROMPT,
    max_turns: int = 15,
) -> str:
    """Send query to the agent.

    Args:
        query: Query to send.
        tools: List of available tools to the agent.
        model: Model ID.
        messages: The agent's message history.
        system_prompt: Agent's system prompt.  Ignored if messages is provided.
        max_turns: The maximum number of turns.

    Returns:
        The agent's final response.

    Raises:
        CompletionError: if HTTPError occured
        NoResponseError: if agent did not produce a response.
        TurnLimitExceededError: if the maximum number of turns are exceeded.
        URLError
    """

    tool_registry = ToolRegistry(tools)
    function_tools = [tool_to_function_tool(tool) for tool in tools]
    turn = 0

    message = None

    if not messages:
        system_message: SystemMessage = {
            "role": "system",
            "content": system_prompt,
        }
        messages.append(system_message)

    user_message: Message = {"role": "user", "content": query}
    messages.append(user_message)

    while turn < max_turns:
        try:
            response = completion(
                model=model,
                messages=messages,
                tools=function_tools,
            )
            finish_reason = response["finish_reason"]
        except NoFinishReasonError as e:
            response = e.response
            finish_reason = None
        except CompletionError:
            raise
        except URLError:
            raise

        assistant_response = response["message"]

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
            case None:
                break
        turn += 1

    if turn >= max_turns:
        raise TurnLimitExceededError(agent_response=message)

    if message is None:
        raise NoResponseError()

    return message
