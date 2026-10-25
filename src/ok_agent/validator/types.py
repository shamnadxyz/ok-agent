from typing import Literal, NotRequired, TypedDict

type SchemaType = Literal['array', 'boolean', 'integer', 'number', 'object', 'string']


class ObjectSchema(TypedDict):
    type: Literal['object']
    description: NotRequired[str]
    properties: NotRequired[dict[str, 'JSONSchema']]
    required: NotRequired[list[str]]
    additionalProperties: NotRequired[bool]


class ArraySchema(TypedDict):
    type: Literal['array']
    description: NotRequired[str]
    items: NotRequired['JSONSchema']
    minItems: NotRequired[int]


class StringSchema(TypedDict):
    type: Literal['string']
    description: NotRequired[str]
    minLength: NotRequired[int]
    maxLength: NotRequired[int]


class NumberSchema(TypedDict):
    type: Literal['number']
    description: NotRequired[str]
    minimum: NotRequired[int]
    maximum: NotRequired[int]


class IntegerSchema(TypedDict):
    type: Literal['integer']
    description: NotRequired[str]
    minimum: NotRequired[int]
    maximum: NotRequired[int]


class BooleanSchema(TypedDict):
    type: Literal['boolean']
    description: NotRequired[str]


type JSONSchema = (
    ObjectSchema
    | ArraySchema
    | StringSchema
    | NumberSchema
    | IntegerSchema
    | BooleanSchema
)
