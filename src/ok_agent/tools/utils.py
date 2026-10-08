from ok_agent.tools.types import (
    ArgumentFormat,
    ArgumentState,
    FormatSpec,
    Tool,
    ToolDisplayState,
)
from ok_agent.utils import format_text


def is_complete(name: str, state: ToolDisplayState) -> bool:
    """Returns whether the streaming of the argument is complete.

    Args:
        name: Name of the argument field.
        state: Dictionary used to track the state of streaming.
    """
    argument_states = state.get("argument_states")
    argument_state = argument_states.get(name) or {}
    return argument_state.get("is_complete") or False


def format_tool_call(
    arguments: dict,
    state: ToolDisplayState,
    tool: Tool,
) -> str | None:
    """Returns formatted tool call for displaying.

    Args:
        state: Used to track the progress of printed tool argument.
        arguments: Tool request JSON string.
    """

    format_spec: FormatSpec | None = tool.get("format_spec")

    if not format_spec:
        return None

    prefix = format_spec["prefix"]
    argument_formats = format_spec.get("arguments")

    if not argument_formats:
        return None

    if all(
        is_complete(argument["name"], state) for argument in argument_formats
    ):
        return None

    formatted_texts = []

    if not state.get("initialized"):
        state["initialized"] = True
        formatted_texts.append(format_text(prefix, "SPECIAL"))

    formatted_texts.extend(
        argument_text
        for argument_text in (
            handle_argument_display(
                argument_format=argument_format,
                state=state,
                arguments=arguments,
            )
            for argument_format in argument_formats
        )
        if argument_text is not None
    )

    if not formatted_texts:
        return None

    return "".join(formatted_texts)


def handle_argument_display(
    argument_format: ArgumentFormat,
    arguments: dict,
    state: ToolDisplayState,
) -> str | None:
    """Display streaming argument and track progress.

    Args:
        argument_format: Format specification for tool call arguments.
        arguments: Parsed arguments dictionary
        state: State dictionary for tracking progress.
    """

    name = argument_format["name"]
    style = argument_format.get("style")
    ensure_newline = argument_format.get("ensure_newline", True)

    if name not in arguments:
        return None

    argument_states = state["argument_states"]
    argument_state = argument_states.get(name)

    if not argument_state:
        argument_state: ArgumentState = {"is_complete": False, "offset": 0}
        argument_states[name] = argument_state

    if argument_state["is_complete"]:
        return None

    offset = argument_state["offset"]

    argument: str = arguments[name]
    argument_length = len(argument)

    if argument_length == 0:
        return None

    if offset != 0 and offset == argument_length:
        argument_state["is_complete"] = True

        if ensure_newline and not argument.endswith("\n"):
            return "\n"

    slice = argument[offset:]

    argument_state["offset"] = argument_length

    return format_text(slice, style)
