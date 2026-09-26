import json
from logging import getLogger

from ok_agent.tools.edit_tool import edit_tool
from ok_agent.tools.read_tool import read_tool
from ok_agent.tools.shell_tool import shell_tool
from ok_agent.tools.types import (
    SchemaType,
    Tool,
    ToolRegistry,
)
from ok_agent.tools.write_tool import write_tool

logger = getLogger(__name__)

from ok_agent.tools.types import JSONSchema


def is_type(data, type: SchemaType) -> bool:
    type_map = {
        "array": list,
        "boolean": bool,
        "integer": int,
        "number": (int, float),
        "object": dict,
        "string": str,
    }

    mapped_type = type_map.get(type)

    if mapped_type is None:
        return False

    return isinstance(data, mapped_type)


def _check_arguments(arguments: list[str], data) -> str | None:
    missing_arguments = [
        argument for argument in arguments if argument not in data
    ]

    if missing_arguments:
        return "Missing required fields: " + ", ".join(missing_arguments)


def _validate_array(data: list, schema: JSONSchema):
    items = schema.get("items")

    if items is None:
        return

    type = items.get("type")

    if not all(is_type(item, type) for item in data):
        return f"Each item in the array should be {type}"


def _validate_object(data: dict, schema: JSONSchema) -> str | None:
    properties = schema.get("properties")

    if properties is None:
        return None

    required_arguments = schema.get("required", [])

    error_message = _check_arguments(required_arguments, data)
    if error_message:
        return error_message

    validation_fails = []
    for property, property_schema in properties.items():
        if property not in data:
            continue

        value = data[property]

        type = property_schema.get("type")

        if not is_type(value, type):
            validation_fails.append(f"{property} should be {type}")
            continue

        if type == "array":
            error_message = _validate_array(value, property_schema)
            if error_message:
                validation_fails.append(f"{property}: {error_message}")

        elif type == "object":
            error_message = _validate_object(value, property_schema)
            if error_message:
                validation_fails.append(f"{property}: {error_message}")

    if validation_fails:
        return "Validation failed: " + "\n".join(validation_fails)


def validate_tool(data: dict, schema: JSONSchema) -> str | None:
    return _validate_object(data, schema)


def execute_tool(name: str, arguments: str, registry: ToolRegistry) -> str:
    tool = registry.get(name)

    if tool is None:
        message = f"tool: '{name}' not found"
        logger.error(message)
        return message

    function = tool.get("function")

    try:
        args = json.loads(arguments)

        error_message = validate_tool(args, tool["parameters"])
        if error_message:
            return error_message

        return function(**args)

    except json.JSONDecodeError as e:
        logger.exception("JSON decode error")
        return f"Invalid arguments JSON: {e}"

    except TypeError as e:
        return f"Inappropriate argument type: {e}"

    except Exception as e:  # noqa: BLE001
        return f"Tool call failed: {type(e).__name__}: {e}"


def get_tools() -> list[Tool]:
    return [read_tool, write_tool, shell_tool, edit_tool]


def create_registry(tools: list[Tool]) -> ToolRegistry:
    return {tool["name"]: tool for tool in tools}
