from ok_agent.validator.types import JSONSchema, SchemaType


def _is_type(data, schema_type: SchemaType) -> bool:
    type_checkers = {
        "array": list,
        "boolean": bool,
        "integer": int,
        "number": [int, float],
        "object": dict,
        "string": str,
    }

    mapped_type = type_checkers.get(schema_type)

    if mapped_type is None:
        return False

    if isinstance(mapped_type, list):
        return type(data) in mapped_type

    return type(data) == mapped_type


def _check_arguments(arguments: list[str], data) -> str | None:
    missing_arguments = [
        argument for argument in arguments if argument not in data
    ]

    if missing_arguments:
        raise ValidationError(
            f"missing required keys: {', '.join(missing_arguments)}"
        )


class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message


def validate_array(data: list, schema: JSONSchema) -> None:
    """Validate array schema.

    Only support single type across one dimensional array.

    Args:
        data: list
        schema: JSON schema of the array

    Raises:
        ValidationError: if wrong type present in the list
    """
    items = schema.get("items")

    if items is None:
        return

    item_type = items.get("type")

    if not all(_is_type(item, item_type) for item in data):
        raise ValidationError(f"each item in the array should be '{item_type}'")


def validate_object(data: dict, schema: JSONSchema) -> None:
    """Validate object schema.

    Args:
        data: dict

    Raises:
        ValidationError: if schema validation fails against the data
    """
    properties = schema.get("properties")

    if properties is None:
        return

    required_arguments = schema.get("required", [])

    validation_fails = []

    additional_properties = schema.get("additionalProperties")
    if additional_properties == False and (
        extra_properties := [key for key in data if key not in properties]
    ):
        validation_fails.append(
            f"extra properties found: {','.join(extra_properties)}"
        )

    try:
        _check_arguments(required_arguments, data)
    except ValidationError as e:
        validation_fails.append(e.message)

    for property, property_schema in properties.items():
        if property not in data:
            continue

        value = data[property]

        type = property_schema.get("type")

        if not _is_type(value, type):
            validation_fails.append(f"{property} should be {type}")
            continue

        if type == "array":
            try:
                validate_array(value, property_schema)
            except ValidationError as e:
                validation_fails.append(f"{property}: {e.message}")

        elif type == "object":
            try:
                validate_object(value, property_schema)
            except ValidationError as e:
                validation_fails.append(f"{property}: {e.message}")

    if validation_fails:
        raise ValidationError("\n".join(validation_fails))
