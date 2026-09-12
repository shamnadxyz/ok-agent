from collections.abc import Callable
from typing import TypedDict

from ok_agent.openai.types import FunctionTool

type Tools = dict[str, Callable]


class Tool(TypedDict):
    name: str
    tool: Callable
    schema: FunctionTool
