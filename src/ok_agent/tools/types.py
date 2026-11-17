from collections.abc import Callable
from dataclasses import dataclass

from ok_agent.utils import Style
from ok_agent.validator import JSONSchema


@dataclass(slots=True)
class ArgumentState:
    """Argument display state.

    Attributes:
        is_complete: If completed printing argument.
        offset: Length of previously displayed argument slice.
        ends_with_newline: Whether the displayed argument ends with a newline.
    """

    is_complete: bool = False
    initialized: bool = False
    offset: int = 0
    ends_with_newline: bool = False


@dataclass(slots=True)
class ToolDisplayState:
    """Tool display state.

    Attributes:
        states: Dictionary of argument states.
        current_argument: Currently formatting argument name.
    """

    argument_states: dict[str, ArgumentState]
    current_argument: str | None = None
    initialized: bool = False


type ToolDisplayStates = dict[int, ToolDisplayState]


@dataclass(frozen=True)
class ArgumentFormat:
    """Specification for the display format of a tool call argument.

    Attributes:
        style: Style to use for formatting.
        ensure_newline: Whether to print a newline after the end of the argument.
    """

    style: Style | None = None
    prefix: str | None = None
    ensure_newline: bool = True


@dataclass(frozen=True, slots=True)
class FormatSpec:
    """Specification for the display format of the tool call.

    Attributes:
        prefix: Initial text to print.
        arguments: Dictionary of argument format specifications.
    """

    prefix: str
    arguments: dict[str, ArgumentFormat]


@dataclass(frozen=True, slots=True)
class Tool:
    """Tool specification.

    Attributes:
        name: Tool name.
        description: Tool description.
        parameters: JSON schema for the parameters.
        function: Function to execute.
        format_spec: Specification for the display format of the tool call.
    """

    name: str
    parameters: JSONSchema
    function: Callable
    format_spec: FormatSpec
    description: str | None = None
