import textwrap
from collections.abc import Generator
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any

from ok_agent.llama_cpp.completions import (
    CompletionError,
    NoFinishReasonError,
    create_chat_completion,
)
from ok_agent.llama_cpp.tools import (
    tool_to_function_tool,
)
from ok_agent.llama_cpp.types import (
    AssistantMessage,
    ChatCompletionChunk,
    CompletionTimings,
    CompletionUsage,
    Content,
    FinishReason,
    Message,
    MessageToolCallChunk,
    SystemMessage,
    ToolMessage,
    is_assistant_message,
)
from ok_agent.skills import SkillMetadata, skills_to_xml
from ok_agent.tools import (
    ToolDisplayState,
    ToolDisplayStates,
    ToolRegistry,
    format_tool_call,
)
from ok_agent.tools.display import display_tool_result
from ok_agent.utils import display_text

logger = getLogger(__name__)


class AgentError(Exception):
    """Common base class for all agent exceptions."""


class NoResponseError(AgentError):
    """Raised when the agent fails to produce a content response."""


class LimitError(AgentError):
    """Limit exceeded exceptions.

    Attributes:
        message: The agent response from the last turn.
    """

    def __init__(
        self,
        message: str,
    ):
        super().__init__(message)


class TokenLimitError(LimitError):
    """Raised when the finish reason is length."""


class TurnLimitError(LimitError):
    """Raised when the maximum number of turns are exceeded.

    Attributes:
        agent_response: The agent response from the last turn.
    """

    def __init__(
        self,
        turn: int,
        turn_limit: int,
    ):
        self.turn = turn
        self.turn_limit = turn_limit

        super().__init__(
            f'Turn limit reached: {self.turn}/{self.turn_limit}',
        )


type ToolCallMap = dict[int, MessageToolCallChunk]


@dataclass(slots=False)
class Response:
    message: AssistantMessage
    finish_reason: FinishReason
    model: str
    created_timestamp: int
    finished_timestamp: int
    timings: CompletionTimings | None = None
    usage: CompletionUsage | None = None


def get_system_prompt(skills: list[SkillMetadata] | None = None) -> SystemMessage:
    agents = Path('AGENTS.md')

    system_message: Content = [
        {
            'type': 'text',
            'text': textwrap.dedent(f"""\
                You are a helpful coding agent. 

                cwd:"{Path.cwd()}"
                Tools will be run relative to this directory.
                """),
        },
    ]

    if agents.exists():
        try:
            content = agents.read_text(encoding='utf-8')
            system_message.append({'type': 'text', 'text': content})
        except (OSError, ValueError):
            logger.exception('Error in reading AGENTS.md file')

    if skills and (formatted_skills := skills_to_xml(skills)):
        system_message.append({'type': 'text', 'text': formatted_skills})

    return {'role': 'system', 'content': system_message}


def _remove_reasoning(assistant_message: AssistantMessage) -> AssistantMessage:
    """Returns assistant message with reasoning_content removed."""
    message: AssistantMessage = {**assistant_message}
    message.pop('reasoning_content', None)
    return message


def clear_reasoning(messages: list[Message]) -> list[Message]:
    """Returns message history with reasoning_content removed.

    Args:
        messages: Message history.
    """
    return [
        _remove_reasoning(message) if is_assistant_message(message) else message
        for message in messages
    ]


def _parse_tool_call_delta(
    tool_calls: list[MessageToolCallChunk],
    map: ToolCallMap,
    display_states: ToolDisplayStates,
    tool_registry: ToolRegistry,
) -> None:
    for tool_call in tool_calls:
        index = tool_call['index']

        function = tool_call.get('function')
        id = tool_call.get('id')
        tool_type = tool_call.get('type')

        if index not in map:
            map[index] = {
                'index': index,
            }

        if index not in display_states:
            display_states[index] = ToolDisplayState({})

        if id is not None:
            map[index]['id'] = id

        if tool_type is not None:
            map[index]['type'] = tool_type

        if function is not None:
            name = function.get('name')
            arguments = function.get('arguments')

            if name is not None:
                map[index]['function'] = {
                    'name': name,
                    'arguments': '',
                }

            if arguments is not None:
                map[index]['function']['arguments'] += arguments

                if text := format_tool_call(
                    argument_chunk=arguments,
                    tool_call=map[index],
                    state=display_states[index],
                    tool_registry=tool_registry,
                ):
                    display_text(text, end='')


def _handle_completion_chunks(
    chunks: Generator[ChatCompletionChunk], tool_registry: ToolRegistry
) -> Response:
    finish_reason: FinishReason | None = None
    model = ''
    usage: CompletionUsage | None = None
    timings: CompletionTimings | None = None
    created_timestamp = 0
    finished_timestamp = 0

    reasoning_parts: list[str] = []
    content_parts: list[str] = []

    reasoning_complete = False
    content_complete = False

    tool_calls_map: ToolCallMap = {}
    tool_display_states: ToolDisplayStates = {}

    assistant_message: AssistantMessage = {'role': 'assistant'}

    for chunk in chunks:
        choices = chunk['choices']
        if not created_timestamp:
            created_timestamp = chunk['created']

        if isinstance(choices, list) and len(choices) == 0:
            if 'usage' in chunk:
                usage = chunk['usage']
            if 'timings' in chunk:
                timings = chunk['timings']
            if 'model' in chunk:
                model = chunk['model']

            finished_timestamp = chunk['created']
            continue

        choice = choices[0]

        if stop_reason := choice.get('finish_reason'):
            finish_reason = stop_reason

        delta = choice.get('delta')

        reasoning_delta = delta.get('reasoning_content')
        content_delta = delta.get('content')

        if reasoning_delta is not None:
            display_text(reasoning_delta, style='DIM', end='')
            reasoning_parts.append(reasoning_delta)
        elif not reasoning_complete and reasoning_parts:
            display_text()
            reasoning_complete = True

        if content_delta is not None:
            display_text(content_delta, end='')
            content_parts.append(content_delta)
        elif not content_complete and content_parts:
            display_text()
            content_complete = True

        if 'tool_calls' in delta:
            _parse_tool_call_delta(
                tool_calls=delta['tool_calls'],
                map=tool_calls_map,
                display_states=tool_display_states,
                tool_registry=tool_registry,
            )

    display_text()

    if finish_reason is None:
        raise NoFinishReasonError('finish_reason missing')

    if reasoning_parts:
        assistant_message['reasoning_content'] = ''.join(reasoning_parts)

    if content_parts:
        assistant_message['content'] = ''.join(content_parts)

    if tool_calls_map:
        assistant_message['tool_calls'] = [
            {
                'id': chunk['id'],
                'type': chunk['type'],
                'function': {
                    'name': chunk['function']['name'],
                    'arguments': chunk['function']['arguments'],
                },
            }
            for _, chunk in sorted(tool_calls_map.items())
        ]

    return Response(
        message=assistant_message,
        finish_reason=finish_reason,
        model=model,
        created_timestamp=created_timestamp,
        finished_timestamp=finished_timestamp,
        timings=timings,
        usage=usage,
    )


def run_agent(
    api_base_url: str,
    api_key: str,
    model: str,
    message_history: list[Message],
    preserve_reasoning: bool,
    show_tool_result: bool,
    tool_registry: ToolRegistry | None = None,
    response_format: dict[str, Any] | None = None,
    query: str | None = None,
    max_turns: int = 15,
) -> str:
    """Send query to the agent.

    Args:
        api_base_url: OpenAI compatible API endpoint.
        api_key: API key.
        query: Query to send.
        tool_registry: Tool registry available to the agent.
        model: Model ID.
        message_history: The agent's message history.
        preserve_reasoning: whether to send back the reasoning content.
        response_format: JSON schema for model output.
        max_turns: The maximum number of turns.

    Returns:
        The agent's final response.

    Raises:
        CompletionError: if HTTPError occured
        NoResponseError: if agent did not produce a response.
        TurnLimitError: if the maximum number of turns are exceeded.
        TokenLimitError: if the maximum token limit is reached.
        URLError
    """
    function_tools = None

    if tool_registry is not None:
        function_tools = [tool_to_function_tool(tool) for tool in tool_registry.tools]
    else:
        tool_registry = ToolRegistry([])

    turn = 0

    message = None

    if query:
        user_message: Message = {'role': 'user', 'content': query}
        message_history.append(user_message)

    kwargs = {
        'preserve_thinking': preserve_reasoning,
    }

    messages = (
        message_history.copy()
        if preserve_reasoning
        else clear_reasoning(message_history)
    )

    while turn < max_turns:
        try:
            completion_chunks = create_chat_completion(
                api_base_url=api_base_url,
                api_key=api_key,
                model=model,
                messages=messages,
                tools=function_tools,
                response_format=response_format,
                chat_template_kwargs=kwargs,
            )

            response = _handle_completion_chunks(completion_chunks, tool_registry)
        except NoFinishReasonError as e:
            raise CompletionError('Missing finish_reason') from e

        assistant_response = response.message

        # Store content response for returning as the final response
        if 'content' in assistant_response:
            message = assistant_response['content']

        if response.finish_reason == 'stop':
            if 'content' not in assistant_response:
                raise CompletionError('missing content')

            message_history.append(assistant_response)
            break

        elif response.finish_reason == 'tool_calls':
            if 'tool_calls' not in assistant_response:
                raise CompletionError('missing tool_calls')

            message_history.append(assistant_response)

            messages.append(
                assistant_response
                if preserve_reasoning
                else _remove_reasoning(assistant_response)
            )

            tool_results: list[ToolMessage] = [
                {
                    'role': 'tool',
                    'tool_call_id': tool_call['id'],
                    'content': tool_registry.execute_tool(
                        tool_call['function']['name'],
                        tool_call['function']['arguments'],
                    ),
                }
                for tool_call in assistant_response['tool_calls']
            ]
            message_history.extend(tool_results)
            messages.extend(tool_results)

            if show_tool_result:
                display_tool_result(tool_results)

        elif response.finish_reason == 'length':
            raise TokenLimitError(
                'Maximum token limit reached',
            )
        else:
            message = f'Unexpected finish_reason: {response.finish_reason}'
            logger.warning(message)
            display_text(message, style='ERROR')
            raise CompletionError(message)

        turn += 1

    if turn >= max_turns:
        raise TurnLimitError(
            turn=turn,
            turn_limit=max_turns,
        )

    if message is None:
        raise NoResponseError('Model failed to produce a response')

    return message
