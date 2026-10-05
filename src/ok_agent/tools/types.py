from collections.abc import Callable
from typing import NotRequired, Protocol, TypedDict

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


class DisplayArguments(Protocol):
    def __call__(self, arguments: str, state: ToolDisplayState) -> None: ...


class Tool(TypedDict):
    """Agent Tool.

    Attributes:
        name: Tool name.
        description: Tool description.
        parameters: JSON schema for the parameters.
        function: Function to execute.
        display_arguments: Function to display tool request using arguments.
    """

    name: str
    description: NotRequired[str]
    parameters: JSONSchema
    function: Callable
    display_arguments: NotRequired[DisplayArguments]
