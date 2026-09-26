from collections.abc import Callable
from typing import Literal, NotRequired, TypedDict

type SchemaType = Literal[
    "array", "boolean", "integer", "number", "object", "string"
]


class ObjectSchema(TypedDict):
    type: Literal["object"]
    description: NotRequired[str]
    properties: NotRequired[dict[str, "JSONSchema"]]
    required: NotRequired[list[str]]


class ArraySchema(TypedDict):
    type: Literal["array"]
    description: NotRequired[str]
    items: "JSONSchema"
    minItems: NotRequired[int]
    uniqueItems: NotRequired[bool]


class StringSchema(TypedDict):
    type: Literal["string"]
    description: NotRequired[str]


class NumberSchema(TypedDict):
    type: Literal["number"]
    description: NotRequired[str]
    minimum: NotRequired[int]
    maximum: NotRequired[int]


class IntegerSchema(TypedDict):
    type: Literal["integer"]
    description: NotRequired[str]
    minimum: NotRequired[int]
    maximum: NotRequired[int]


class BooleanSchema(TypedDict):
    type: Literal["boolean"]
    description: NotRequired[str]


type JSONSchema = (
    ObjectSchema
    | ArraySchema
    | StringSchema
    | NumberSchema
    | IntegerSchema
    | BooleanSchema
)
type ToolRegistry = dict[str, Tool]


class Tool(TypedDict):
    name: str
    description: NotRequired[str]
    parameters: JSONSchema
    function: Callable
