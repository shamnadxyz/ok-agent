from typing import Literal, NotRequired, TypedDict

Role = Literal["user", "tool", "assistant", "system"]


ToolType = Literal["function"]


class Function(TypedDict):
    name: str
    arguments: str


class MessageToolCall(TypedDict):
    id: str
    type: ToolType
    function: Function


class FunctionDefinition(TypedDict):
    """Tool JSON schema."""

    name: str
    description: NotRequired[str]
    parameters: NotRequired[dict]
    strict: NotRequired[bool | None]


class FunctionTool(TypedDict):
    """Tool that can be used to generate a response sent to the LLM."""

    type: ToolType
    function: FunctionDefinition


class PromptCacheBreakpoint(TypedDict):
    mode: Literal["explicit"]


class ContentPartText(TypedDict):
    type: Literal["text"]
    text: str
    prompt_cache_breakpoint: NotRequired[PromptCacheBreakpoint]


class SystemMessage(TypedDict):
    role: Literal["system"]
    content: str | list[ContentPartText]


class UserMessage(TypedDict):
    role: Literal["user"]
    content: str | list[ContentPartText]
    name: NotRequired[str]


class AssistantMessage(TypedDict):
    role: Literal["assistant"]
    content: NotRequired[str | ContentPartText]
    name: NotRequired[str]
    refusal: NotRequired[str | None]
    tool_calls: NotRequired[list[MessageToolCall]]


class ToolMessage(TypedDict):
    role: Literal["tool"]
    tool_call_id: str
    content: str | list[ContentPartText]


Message = SystemMessage | UserMessage | AssistantMessage | ToolMessage


class ResponseResult(TypedDict, total=False):
    content: str | ContentPartText
    tool_calls: list[MessageToolCall]
