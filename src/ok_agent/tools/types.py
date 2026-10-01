from collections.abc import Callable
from typing import NotRequired, TypedDict

from ok_agent.validator import JSONSchema


class Tool(TypedDict):
    name: str
    description: NotRequired[str]
    parameters: JSONSchema
    function: Callable
