from typing import Literal, NotRequired, TypedDict

from ok_agent.validator import JSONSchema

type Role = Literal["user", "tool", "assistant", "system"]
type FinishReason = Literal["length", "stop", "tool_calls"]
type ToolType = Literal["function"]


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
    parameters: NotRequired[JSONSchema]


class FunctionTool(TypedDict):
    """Tool sent to the LLM."""

    type: ToolType
    function: FunctionDefinition


class ContentPartText(TypedDict):
    type: Literal["text"]
    text: str


class ImageUrl(TypedDict):
    url: str


class ContentPartImage(TypedDict):
    type: Literal["image_url"]
    image_url: ImageUrl


type Content = str | list[ContentPartText | ContentPartImage]


class SystemMessage(TypedDict):
    role: Literal["system"]
    content: Content


class UserMessage(TypedDict):
    role: Literal["user"]
    content: Content
    name: NotRequired[str]


class ToolMessage(TypedDict):
    role: Literal["tool"]
    tool_call_id: str
    content: Content


class AssistantMessage(TypedDict):
    role: Literal["assistant"]
    content: NotRequired[str]
    reasoning_content: NotRequired[str]
    tool_calls: NotRequired[list[MessageToolCall]]


type Message = SystemMessage | UserMessage | AssistantMessage | ToolMessage


class Response(TypedDict, total=False):
    message: AssistantMessage
    finish_reason: FinishReason
