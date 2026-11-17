from logging import getLogger

from ok_agent.llama_cpp.types import FunctionTool
from ok_agent.tools import Tool

logger = getLogger(__name__)


def tool_to_function_tool(tool: Tool) -> FunctionTool:
    """Converts Tool object to OpenAI ChatCompletionFunctionTool."""
    function_tool: FunctionTool = {
        'type': 'function',
        'function': {
            'name': tool.name,
            'parameters': tool.parameters,
        },
    }

    if tool.description is not None:
        function_tool['function']['description'] = tool.description

    return function_tool
