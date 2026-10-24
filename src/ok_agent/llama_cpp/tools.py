from logging import getLogger

from ok_agent.config import get_config
from ok_agent.llama_cpp.types import FunctionTool, MessageToolCall, ToolMessage
from ok_agent.tools import ToolRegistry
from ok_agent.tools.utils import format_tool_call
from ok_agent.utils import clear_lines_above, display_text

logger = getLogger(__name__)


def tools_to_function_tools(tool_registry: ToolRegistry) -> list[FunctionTool]:
    """Convert Tools from ToolRegistry to OpenAI ChatCompletionFunctionTool."""
    function_tools: list[FunctionTool] = []
    tools = tool_registry.get_tools()

    for tool in tools:
        function: FunctionTool = {
            'type': 'function',
            'function': {
                'name': tool['name'],
                'parameters': tool['parameters'],
            },
        }

        if 'description' in tool:
            function['function']['description'] = tool['description']

        function_tools.append(function)

    return function_tools


def handle_tool_calls(
    tool_registry: ToolRegistry,
    tool_calls: list[MessageToolCall],
) -> list[ToolMessage]:

    config = get_config()

    tool_messages: list[ToolMessage] = []

    tool_texts: list[str] = []
    newlines = 0

    for tool_call in tool_calls:
        function = tool_call.get('function')
        arguments_json = function.get('arguments')
        name = function.get('name')

        tool_content = tool_registry.execute_tool(name, arguments_json)

        tool_call_id = tool_call['id']

        tool_message: ToolMessage = {
            'role': 'tool',
            'tool_call_id': tool_call_id,
            'content': tool_content,
        }

        tool_messages.append(tool_message)

        logger.debug({**tool_message, 'name': name, 'arguments': arguments_json})

        formatted_tool_args = format_tool_call(
            tool_call=tool_call,
            state={'initialized': False, 'argument_states': {}},
            is_final=True,
        )

        if formatted_tool_args is not None:
            newlines += len(formatted_tool_args.splitlines())

            if isinstance(tool_content, str):
                text_content = tool_content
            else:
                text_content = ''.join(
                    content['text']
                    for content in tool_content
                    if content['type'] == 'text'
                )

            formatted_tool_call = f'{formatted_tool_args}{text_content}'

            tool_texts.append(formatted_tool_call)

    if config.show_tool_result:
        clear_lines_above(count=newlines)

        for text in tool_texts:
            display_text(text)

    return tool_messages
