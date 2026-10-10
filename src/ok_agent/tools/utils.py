import json

from ok_agent.llama_cpp.types import MessageToolCall
from ok_agent.tools import TOOL_REGISTRY, ToolNotFoundError
from ok_agent.tools.types import (
    ArgumentFormat,
    ArgumentState,
    FormatSpec,
    ToolDisplayState,
)
from ok_agent.utils import display_text, format_text


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
    tool_call: MessageToolCall,
    state: ToolDisplayState,
    is_final: bool = False,
) -> str | None:
    """Returns formatted tool call for displaying.

    Args:
        state: Used to track the progress of printed tool argument.
        arguments: Tool request JSON string.
        is_final: If parsing the complete tool_call.
    """

    completed_arguments = rescue_partial_json(
        tool_call["function"]["arguments"]
    )

    if completed_arguments is None:
        return

    try:
        arguments = json.loads(completed_arguments)
    except json.JSONDecodeError:
        return

    try:
        tools = TOOL_REGISTRY.get_tools([tool_call["function"]["name"]])
    except ToolNotFoundError as e:
        display_text(str(e), "ERROR")
        return

    tool = tools[0]

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
                is_final=is_final,
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
    is_final: bool = False,
) -> str | None:
    """Display streaming argument and track progress.

    Args:
        argument_format: Format specification for tool call arguments.
        arguments: Parsed arguments dictionary
        state: State dictionary for tracking progress.
        is_final: If parsing the final complete arguments dictionary.
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

    if offset != 0 and offset == argument_length or is_final:
        argument_state["is_complete"] = True

    slice = argument[offset:]

    if (
        argument_state["is_complete"]
        and ensure_newline
        and not argument.endswith("\n")
    ):
        if is_final:
            return format_text(f"{slice}\n", style)
        else:
            return "\n"

    argument_state["offset"] = argument_length

    return format_text(slice, style)


def rescue_partial_json(string: str) -> str | None:
    """Scans through the JSON string and adds the missing closing delimiters.

    Args:
        string: incomplete JSON string.

    Returns:
        Completed JSON string or None if a closing delimiter is encountered
        without a matching opening delimiter.
    """
    BRACES_OPEN = "{"
    BRACES_CLOSE = "}"
    BRACKET_OPEN = "["
    BRACKET_CLOSE = "]"
    QUOTE = '"'
    BACKSLASH = "\\"

    open_delimiters: list[str] = []
    escape_next = False
    in_string = False

    for char in string:
        if escape_next:
            escape_next = False
            continue

        if char == BACKSLASH:
            escape_next = True
            continue

        if char == QUOTE:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == BRACES_OPEN or char == BRACKET_OPEN:
            open_delimiters.append(char)
        elif char == BRACES_CLOSE:
            if not open_delimiters or open_delimiters[-1] != BRACES_OPEN:
                return None
            open_delimiters.pop()
        elif char == BRACKET_CLOSE:
            if not open_delimiters or open_delimiters[-1] != BRACKET_OPEN:
                return None
            open_delimiters.pop()

    if in_string:
        open_delimiters.append(QUOTE)

    if not open_delimiters:
        return string

    # Add the closing delimiters
    for char in reversed(open_delimiters):
        if char == BRACES_OPEN:
            string += BRACES_CLOSE
        elif char == BRACKET_OPEN:
            string += BRACKET_CLOSE
        else:
            string += QUOTE

    return string
