from collections.abc import Callable
from typing import NotRequired, TypedDict

from ok_agent.utils import Style
from ok_agent.validator import JSONSchema


class ArgumentState(TypedDict):
    """Argument display state.

    Attributes:
        is_complete: If completed printing argument.
        offset: Length of previously displayed argument slice.
    """

    is_complete: bool
    offset: int


class ToolDisplayState(TypedDict):
    """Tool call display state.

    Attributes:
        initialized: If printed initial message.
        argument_states: Display states of arguments.
    """

    initialized: bool
    argument_states: dict[str, ArgumentState]


type ToolDisplayStates = dict[str, ToolDisplayState]


class ArgumentFormat(TypedDict):
    """Specification for the display format of the tool call arguments.

    Attributes:
        name: Argument field name.
        style: Style to use for formatting.
        ensure_newline: Ensure newline is printed at the end of the argument.
    """

    name: str
    style: NotRequired[Style]
    ensure_newline: NotRequired[bool]


class FormatSpec(TypedDict):
    """Specification for the display format of the tool call.

    Attributes:
        prefix: Initial text to print.
        arguments: List of argument format specifications.
    """

    prefix: str
    arguments: list[ArgumentFormat]


class Tool(TypedDict):
    """Agent Tool.

    Attributes:
        name: Tool name.
        description: Tool description.
        parameters: JSON schema for the parameters.
        function: Function to execute.
        format_spec: Specification for the display format of the tool call.
    """

    name: str
    description: NotRequired[str]
    parameters: JSONSchema
    function: Callable
    format_spec: NotRequired[FormatSpec]
