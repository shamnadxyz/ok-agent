import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from logging import getLogger

from ok_agent.ansi_sequences import GREY, RESET
from ok_agent.config import get_config
from ok_agent.llama_cpp.types import (
    Function,
    FunctionTool,
    Message,
    MessageToolCall,
    Response,
)
from ok_agent.llama_cpp.utils import build_request, get_response_error_message

trace = getLogger("llm.traces")
logger = getLogger(__name__)


class NoFinishReasonError(Exception):
    def __init__(self, response: Response):
        self.response = response


class CompletionError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


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


def _handle_stream(stream: Iterable[bytes]) -> Response:
    """Parses the LLM response and prints it.

    Parses the SSE byte streaming response from the LLM server then prints the
    reasoning content in gray color and prints the output without color.

    Raises:
        NoFinishReasonError: if no finish_reason was received
    """
    role = None
    contents: list[str] = []
    reasoning_contents: list[str] = []
    tool_calls: list[MessageToolCall] = []
    finish_reason = None

    config = get_config()

    for line in stream:
        decoded_response = line.decode("utf-8", errors="ignore").strip()
        trace.debug(decoded_response)
        if decoded_response == "":
            continue

        data = _parse_data(decoded_response)
        if data is None:
            continue

        choices = data.get("choices", [])

        if not choices:
            continue

        choice: dict = choices[0]

        if "finish_reason" in choice:
            finish_reason = choice["finish_reason"]

        delta = choice.get("delta")

        if not delta:
            continue

        if "role" in delta:
            role = delta["role"]

        if "tool_calls" in delta:
            _parse_tool_stream(tool_calls, delta)

        if "reasoning_content" in delta:
            reasoning_content = delta.get("reasoning_content")
            if reasoning_content:
                print(f"{GREY}{reasoning_content}{RESET}", end="", flush=True)
                reasoning_contents.append(reasoning_content)

        if "content" in delta:
            content = delta.get("content")
            if content:
                print(content, end="", flush=True)
                contents.append(content)
    print()

    response: Response = {"message": {"role": role if role else "assistant"}}

    if contents:
        response["message"]["content"] = "".join(contents)

    if tool_calls:
        response["message"]["tool_calls"] = tool_calls

    if reasoning_contents and config.preserve_reasoning:
        response["message"]["reasoning_content"] = "".join(reasoning_contents)

    if not finish_reason:
        raise NoFinishReasonError(response)

    response["finish_reason"] = finish_reason

    trace.debug(response)

    return response


def completion(
    model: str,
    messages: list[Message],
    tools: list[FunctionTool],
    timeout: int = 300,
) -> Response:
    """Sends completion request to messages to llama-cpp server.

    Returns:
        Response with CompletionMessage and finish_reason

    Raises:
        CompletionError: if HTTPError occured
        NoFinishReasonError: if no finish_reason was received
        URLError
    """
    completions_endpoint = "/chat/completions"

    data = json.dumps(
        {
            "model": model,
            "stream": True,
            "tools": tools,
            "messages": messages,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()

    logger.debug(f"Request data: {data}")

    request = build_request(completions_endpoint, data, method="POST")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _handle_stream(response)

    except urllib.error.HTTPError as e:
        error_message = get_response_error_message(e)
        raise CompletionError(message=error_message)

    except urllib.error.URLError:
        raise
