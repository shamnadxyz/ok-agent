from typing import Any, Literal, NotRequired, TypedDict

type SchemaType = Literal['array', 'boolean', 'integer', 'number', 'object', 'string']


class BaseSchema(TypedDict):
    description: NotRequired[str]


class ObjectSchema(BaseSchema):
    type: Literal['object']
    properties: NotRequired[dict[str, 'JSONSchema']]
    required: NotRequired[list[str]]
    additionalProperties: NotRequired[bool]


class ArraySchema(BaseSchema):
    type: Literal['array']
    items: NotRequired['JSONSchema']
    minItems: NotRequired[int]


class StringSchema(BaseSchema):
    type: Literal['string']
    minLength: NotRequired[int]
    maxLength: NotRequired[int]
    enum: NotRequired[list[Any]]


class NumberSchema(BaseSchema):
    type: Literal['number']
    minimum: NotRequired[int]
    maximum: NotRequired[int]
    enum: NotRequired[list[Any]]


class IntegerSchema(BaseSchema):
    type: Literal['integer']
    minimum: NotRequired[int]
    maximum: NotRequired[int]
    enum: NotRequired[list[Any]]


class BooleanSchema(BaseSchema):
    type: Literal['boolean']


type JSONSchema = (
    ObjectSchema
    | ArraySchema
    | StringSchema
    | NumberSchema
    | IntegerSchema
    | BooleanSchema
)
