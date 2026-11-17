import json
import urllib.error
import urllib.request
from collections.abc import Generator
from logging import getLogger
from typing import Any

from ok_agent.llama_cpp.types import (
    ChatCompletionChunk,
    ChatCompletionEvent,
    FunctionTool,
    Message,
    is_error_event,
)
from ok_agent.llama_cpp.utils import (
    build_request,
    get_response_error_message,
)
from ok_agent.sse import parse_event_stream

logger = getLogger(__name__)


class CompletionError(Exception):
    """Base class for completion errors."""


class NoFinishReasonError(Exception):
    """Raised when finish_reason is not found in the response."""


def create_chat_completion(
    api_base_url: str,
    api_key: str,
    model: str,
    messages: list[Message],
    tools: list[FunctionTool] | None = None,
    timeout: int = 300,
    response_format: dict[str, Any] | None = None,
    chat_template_kwargs: dict | None = None,
) -> Generator[ChatCompletionChunk]:
    """Create chat completion request to OpenAI compatible endpoint.

    Args:
        api_base_url: OpenAI compatible API endpoint.
        api_key: API key.
        model: Model ID.
        messages: Message history.
        tools: Tools available to the model.
        timeout: Timeout in seconds.
        response_format: JSON schema for model output.
        chat_template_kwargs: Arguments to the chat template.

    Returns:
        Response with AssistantMessage and finish_reason

    Raises:
        CompletionError: If the request fails, the stream reports an error, or times out.
        URLError
    """
    payload = {
        'model': model,
        'stream': True,
        'messages': messages,
        'stream_options': {'include_usage': True},
    }

    if chat_template_kwargs:
        payload['chat_template_kwargs'] = chat_template_kwargs

    if tools:
        payload['tools'] = tools

    if response_format:
        payload['response_format'] = response_format

    data = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(',', ':'),
        allow_nan=False,
    )

    logger.debug('data: %s', data)

    request = build_request(
        api_base_url=api_base_url,
        api_key=api_key,
        endpoint='/chat/completions',
        data=data.encode('utf-8'),
        method='POST',
    )
    request.add_header('Content-Type', 'application/json')
    request.add_header('Accept', 'text/event-stream')

    try:
        with urllib.request.urlopen(request, timeout=timeout) as stream:
            for event in parse_event_stream(stream):
                if event.data.startswith('[DONE]'):
                    break

                try:
                    data: ChatCompletionEvent = json.loads(event.data)
                except json.JSONDecodeError:
                    logger.exception('Invalid JSON')
                    continue

                if is_error_event(data):
                    error = data['error']
                    raise CompletionError(error.get('message', str(error)))

                yield data

    except urllib.error.HTTPError as e:
        error_message = get_response_error_message(e)
        raise CompletionError(error_message) from e
    except TimeoutError as e:
        raise CompletionError('Completion request timed out') from e
