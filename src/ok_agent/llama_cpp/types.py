from typing import Literal, NotRequired, TypedDict, TypeGuard, TypeIs

from ok_agent.validator import JSONSchema

type Role = Literal['developer', 'system', 'user', 'assistant', 'tool']

type FinishReason = Literal[
    'length',
    'stop',
    'tool_calls',
    'content_filter',
    'function_call',
]

type ToolType = Literal['function']


class Function(TypedDict):
    name: str
    arguments: str


class FunctionChunk(TypedDict, total=False):
    name: str
    arguments: str


class MessageToolCallChunk(TypedDict):
    index: int
    id: NotRequired[str]
    type: NotRequired[ToolType]
    function: NotRequired[FunctionChunk]


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
    type: Literal['text']
    text: str


class ImageUrl(TypedDict):
    url: str


class ContentPartImage(TypedDict):
    type: Literal['image_url']
    image_url: ImageUrl


type Content = str | list[ContentPartText | ContentPartImage]


class SystemMessage(TypedDict):
    role: Literal['system']
    content: Content


class UserMessage(TypedDict):
    role: Literal['user']
    content: Content
    name: NotRequired[str]


class ToolMessage(TypedDict):
    role: Literal['tool']
    tool_call_id: str
    content: Content


class AssistantMessage(TypedDict):
    role: Literal['assistant']
    content: NotRequired[str]
    reasoning_content: NotRequired[str]
    tool_calls: NotRequired[list[MessageToolCall]]


type Message = SystemMessage | UserMessage | AssistantMessage | ToolMessage

type ToolCallMap = dict[int, MessageToolCallChunk]


def is_assistant_message(message: Message) -> TypeGuard[AssistantMessage]:
    return message['role'] == 'assistant'


class CompletionTokensDetails(TypedDict, total=False):
    accepted_prediction_tokens: int
    audio_tokens: int
    reasoning_tokens: int
    rejected_prediction_tokens: int
    text_tokens: int


class PromptTokensDetails(TypedDict, total=False):
    audio_tokens: int
    cache_write_tokens: int
    cached_tokens: int
    image_tokens: int
    text_tokens: int


class CompletionUsage(TypedDict):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    completion_tokens_details: NotRequired[CompletionTokensDetails]
    prompt_tokens_details: NotRequired[PromptTokensDetails]


class CompletionTimings(TypedDict):
    cache_n: int
    prompt_n: int
    prompt_ms: float
    prompt_per_token_ms: float
    prompt_per_second: float
    predicted_n: int
    predicted_ms: float
    predicted_per_token_ms: float
    predicted_per_second: float
    draft_n: NotRequired[int]
    draft_n_accepted: NotRequired[int]


class ChoiceDelta(TypedDict, total=False):
    content: str | None
    reasoning_content: str
    refusal: str | None
    role: Role
    tool_calls: list[MessageToolCallChunk]


class Choice(TypedDict):
    delta: ChoiceDelta
    index: int
    finish_reason: NotRequired[FinishReason | None]


class ChatCompletionChunk(TypedDict):
    id: str
    choices: list[Choice]
    created: int
    model: str
    object: Literal['chat.completion.chunk']
    usage: NotRequired[CompletionUsage | None]
    timings: NotRequired[CompletionTimings]
    system_fingerprint: NotRequired[str]


class ServerError(TypedDict):
    code: int
    message: str
    type: str


class ErrorEvent(TypedDict):
    error: ServerError


type ChatCompletionEvent = ChatCompletionChunk | ErrorEvent


def is_error_event(event: ChatCompletionEvent) -> TypeIs[ErrorEvent]:
    return 'error' in event
