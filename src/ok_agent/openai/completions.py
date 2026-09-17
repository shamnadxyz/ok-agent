import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from http import HTTPStatus
from logging import getLogger

from ok_agent.ansi_sequences import GREY, RED, RESET
from ok_agent.config import get_config
from ok_agent.openai.types import (
    Function,
    FunctionTool,
    Message,
    MessageToolCall,
    ResponseResult,
)

trace = getLogger("llm.traces")
logger = getLogger(__name__)


def _parse_data(event: str) -> dict | None:
    """Extract the json data from the SSE data event.

    Args:
      data_event: SSE data event line
    Returns:
      Object loaded from JSON
    """
    if not event.startswith("data: "):
        return None

    json_data = event.removeprefix("data: ")

    if json_data == "[DONE]":
        return None

    try:
        return json.loads(json_data)

    except json.JSONDecodeError:
        logger.exception("Invalid JSON")
        return None


def _extract_delta(event: str) -> dict | None:
    data = _parse_data(event)

    if data is None:
        return None

    choices = data.get("choices")

    if not choices:
        return None

    choice: dict = choices[0]

    return choice.get("delta")


def _parse_tool_stream(tool_calls: list[MessageToolCall], delta: dict) -> None:
    for tool_call in delta.get("tool_calls", []):
        idx = tool_call.get("index")
        if idx is None:
            continue

        tool_function = tool_call.get("function", {})
        function_name = tool_function.get("name")
        argument = tool_function.get("arguments")

        function_id = tool_call.get("id")
        tool_type = tool_call.get("type")

        if tool_type is not None and tool_type != "function":
            logger.warning(f"Incompatible tool type: {tool_type}")
            print(f"Incompatible tool type: {tool_type}")
            continue

        if function_name is not None and function_id is not None:
            call: Function = {
                "name": function_name,
                "arguments": "",
            }

            function: MessageToolCall = {
                "id": function_id,
                "type": tool_type,
                "function": call,
            }

            logger.debug(f"tool_call: {function}")
            tool_calls.insert(idx, function)

        if argument:
            tool_calls[idx]["function"]["arguments"] += argument


def _handle_response(response: Iterable[bytes]) -> ResponseResult:
    """Parses the LLM response and prints it.

    Parses the SSE byte streaming response from the LLM server then prints the
    reasoning content between think tags in grey color and prints the output
    in normal color.

    Args:
      response: byte stream
    Returns:
      List of Messages containing reasoning and output contents and tool call
      result and a boolean if response contain tool call
    """
    reasoning_content: list[str] = []
    content: list[str] = []
    tool_calls: list[MessageToolCall] = []

    previously_thinking = False

    for line in response:
        decoded_response = line.decode("utf-8").strip()
        if decoded_response == "":
            continue

        delta = _extract_delta(decoded_response)
        if delta is None:
            continue

        if "tool_calls" in delta:
            _parse_tool_stream(tool_calls, delta)

        if "reasoning_content" in delta:
            if not previously_thinking:
                print(GREY, end="")
                previously_thinking = True

            reasoning = delta.get("reasoning_content") or ""
            print(reasoning, end="", flush=True)
            reasoning_content.append(reasoning)
        elif previously_thinking:
            previously_thinking = False
            print(RESET, end="")

        if "content" in delta:
            output = delta.get("content") or ""
            print(output, end="", flush=True)
            content.append(output)
    print()

    result: ResponseResult = {"content": "".join(content)}

    if tool_calls:
        result["tool_calls"] = tool_calls

    trace.debug(
        {
            **result,
            "reasoning_content": "".join(reasoning_content)
            if reasoning_content
            else None,
        }
    )

    return result


def completion(
    messages: list[Message],
    tools: list[FunctionTool],
    model: str | None,
    timeout: int = 300,
) -> ResponseResult | None:
    """Sends the list of messages to LLM server."""
    config = get_config()
    api_base_url = config["api_base_url"]
    completions_endpoint = f"{api_base_url}/chat/completions"

    if model is None:
        model = config["model"]

    data = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": True,
            "tools": tools,
        }
    ).encode("utf-8")

    logger.debug(f"Request data: {data}")

    request = urllib.request.Request(
        completions_endpoint, data=data, method="POST"
    )

    api_key = config["api_key"]
    if api_key is not None:
        request.add_header("Authorization", f"Bearer {api_key}")

    logger.debug(f"Request URL: {request.full_url}")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _handle_response(response)

    except urllib.error.HTTPError as e:
        reason = e.reason

        match e.status:
            case HTTPStatus.UNAUTHORIZED:
                reason = "Unauthorized: invalid API key"

        message = f"{request.method} {request.full_url} {reason}"
        logger.exception(message)

        print(f"{RED}{reason}{RESET}")

        return None
    except urllib.error.URLError as e:
        logger.exception(f"{request.method} {request.full_url}")
        print(f"{RED}{e.reason}{RESET}")
        return None
