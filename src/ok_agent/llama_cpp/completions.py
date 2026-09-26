import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from logging import getLogger

from ok_agent.ansi_sequences import GREY, RESET
from ok_agent.llama_cpp.types import (
    Function,
    FunctionTool,
    Message,
    MessageToolCall,
    ResponseResult,
)
from ok_agent.llama_cpp.utils import build_request, get_error_message
from ok_agent.utils import decode_bytes

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

            tool_calls.insert(idx, function)

        if argument:
            tool_calls[idx]["function"]["arguments"] += argument


def _handle_response(response: Iterable[bytes]) -> ResponseResult:
    """Parses the LLM response and prints it.

    Parses the SSE byte streaming response from the LLM server then prints the
    reasoning content in gray color and prints the output without color.

    Args:
      response: byte stream
    Returns:
      List of Messages containing reasoning and output contents and tool call
      result and a boolean if response contain tool call
    """
    content: list[str] = []
    reasoning_content: list[str] = []
    tool_calls: list[MessageToolCall] = []

    for line in response:
        decoded_response = decode_bytes(line).strip()
        if decoded_response == "":
            continue

        delta = _extract_delta(decoded_response)
        if delta is None:
            continue

        if "tool_calls" in delta:
            _parse_tool_stream(tool_calls, delta)

        if "reasoning_content" in delta:
            reasoning = delta.get("reasoning_content") or ""
            print(f"{GREY}{reasoning}{RESET}", end="", flush=True)
            reasoning_content.append(reasoning)

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
    model: str,
    messages: list[Message],
    tools: list[FunctionTool],
    timeout: int = 300,
) -> ResponseResult | None:
    """Sends completion request to messages to llama-cpp server."""
    completions_endpoint = "/chat/completions"

    data = json.dumps(
        {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": True,
        },
    ).encode("utf-8")

    logger.debug(f"Request data: {data}")

    request = build_request(completions_endpoint, data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _handle_response(response)

    except urllib.error.HTTPError as e:
        message = e.reason
        error_message = get_error_message(e)

        if error_message is not None:
            message = error_message

        logger.exception(message)
        print(message)

        return None
    except urllib.error.URLError as e:
        logger.exception(e.reason)
        print(e.reason)
        return None
