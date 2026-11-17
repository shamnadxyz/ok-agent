import json

from ok_agent.llama_cpp.types import MessageToolCall, MessageToolCallChunk
from ok_agent.tools.registry import ToolNotFoundError, ToolRegistry
from ok_agent.tools.types import (
    ArgumentFormat,
    ArgumentState,
    FormatSpec,
    ToolDisplayState,
)
from ok_agent.tools.utils import rescue_partial_json
from ok_agent.utils import format_text


def format_tool_call(
    argument_chunk: str,
    tool_call: MessageToolCallChunk | MessageToolCall,
    state: ToolDisplayState,
    tool_registry: ToolRegistry,
) -> str | None:
    function = tool_call['function']

    try:
        tool = tool_registry.get_tool(function['name'])
        format_spec = tool.format_spec
    except ToolNotFoundError:
        format_spec = None

    if format_spec is None:
        return argument_chunk

    return _format_tool_call(
        arguments=function['arguments'],
        tool_call_id=tool_call['id'],
        state=state,
        format_spec=format_spec,
    )


def _format_tool_call(
    arguments: str,
    tool_call_id: str,
    state: ToolDisplayState,
    format_spec: FormatSpec,
) -> str | None:
    """Format argument for tool call as per the specfication.

    Args:
        arguments: Tool request JSON string.
        format_spec: Specification for formatting the argument.
        state: For tracking the progress of printed arguments.
    """
    result = rescue_partial_json(arguments)

    try:
        arguments = json.loads(result.json)
    except json.JSONDecodeError:
        return None

    if not isinstance(arguments, dict):
        return None

    text_parts: list[str] = []

    for name, value in arguments.items():
        if type(value) not in (str, int) and not result.is_complete:
            continue

        value = str(value)

        if name not in state.argument_states:
            state.argument_states[name] = ArgumentState()

        argument_state = state.argument_states[name]

        if argument_state.is_complete:
            continue

        if state.current_argument is None:
            state.current_argument = name

        if state.current_argument != name:
            prev_arg_state = state.argument_states[state.current_argument]
            prev_arg_state.is_complete = True
            prev_arg_spec = format_spec.arguments.get(
                state.current_argument, ArgumentFormat()
            )

            if prev_arg_spec.ensure_newline and not prev_arg_state.ends_with_newline:
                text_parts.append('\n')
                prev_arg_state.ends_with_newline = True

            state.current_argument = name

        if not state.initialized:
            text_parts.extend(
                [
                    f'[{tool_call_id}]\n',
                    format_text(format_spec.prefix, style='SPECIAL'),
                ]
            )
            state.initialized = True

        argument_length = len(value)
        argument_spec = format_spec.arguments.get(
            name, ArgumentFormat(prefix=f'{name}: ')
        )

        if not argument_state.initialized and argument_spec.prefix is not None:
            text_parts.append(argument_spec.prefix)
            argument_state.initialized = True

        if argument_length > argument_state.offset:
            part = value[argument_state.offset :]
            text_parts.append(format_text(part, style=argument_spec.style))

            argument_state.offset = argument_length
            argument_state.ends_with_newline = value.endswith('\n')

    if state.current_argument is not None and result.is_complete:
        last_state = state.argument_states[state.current_argument]
        last_spec = format_spec.arguments.get(state.current_argument, ArgumentFormat())

        if (
            not last_state.is_complete
            and last_spec.ensure_newline
            and not last_state.ends_with_newline
        ):
            text_parts.append('\n')
            last_state.ends_with_newline = True

        last_state.is_complete = True

    if text_parts:
        return ''.join(text_parts)

    return None
