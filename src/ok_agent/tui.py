import atexit
import readline
import sys
import termios
from contextlib import contextmanager
from pathlib import Path

from ok_agent.config import Config
from ok_agent.llama_cpp.types import Message, MessageToolCall
from ok_agent.session import Session, refresh_models
from ok_agent.tools import ToolDisplayState, ToolRegistry, format_tool_call
from ok_agent.tools.display import display_tool_result
from ok_agent.utils import content_to_text, display_text


class HistoryMalformedError(Exception):
    """Raised when the message history is malformed."""


@contextmanager
def disable_input():
    """Disables input echo and clears input on exit.

    Disable the terminal ECHO attribute on entry and restores the terminal
    and clears the queued data on STDIN.
    """
    if not sys.stdin.isatty():
        yield
        return

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)

    # Disable the ECHO attribute
    new[3] = new[3] & ~termios.ECHO

    # Restore original terminal attributes
    termios.tcsetattr(fd, termios.TCSADRAIN, new)

    try:
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        # Discard queued data on STDIN
        termios.tcflush(fd, termios.TCIFLUSH)


def _init_completions(session: Session, config: Config):
    commands = ['/model', '/continue', '/refresh-models']

    if session.model is None and session.models is None:
        refresh_models(session, config.api_base_url, config.api_key)

    if session.skills:
        commands.extend(f'/skill:{skill["name"]}' for skill in session.skills)

    def complete(text: str, state: int) -> str | None:
        completions = commands
        if text == '':
            return None

        if text.startswith('/model'):
            if session.models is None:
                refresh_models(session, config.api_base_url, config.api_key)

            if session.models:
                completions = [f'/model {model}' for model in session.models]

        candidates = [command for command in completions if command.startswith(text)]

        if state < len(candidates):
            return candidates[state]
        else:
            return None

    readline.parse_and_bind('tab: complete')
    readline.set_completer(complete)
    readline.set_completer_delims('')


def replay_history(
    messages: list[Message],
    tool_registry: ToolRegistry,
    config: Config,
):
    tool_call_map: dict[str, MessageToolCall] = {}

    for message in messages:
        match message['role']:
            case 'user':
                text = content_to_text(message['content'])
                display_text(f'{config.prompt}', 'SPECIAL', end='')
                display_text(text)

            case 'tool':
                tool_id = message['tool_call_id']
                if tool_id not in tool_call_map:
                    raise HistoryMalformedError(
                        'Tool call not found for the tool result'
                    )

                tool_call = tool_call_map[tool_id]
                if formatted_text := format_tool_call(
                    argument_chunk=tool_call['function']['arguments'],
                    tool_call=tool_call,
                    state=ToolDisplayState({}),
                    tool_registry=tool_registry,
                ):
                    display_text(formatted_text, end='')

                if config.show_tool_result:
                    display_tool_result([message])

            case 'assistant':
                if 'reasoning_content' in message:
                    display_text(message['reasoning_content'], style='DIM')

                if 'content' in message:
                    display_text(message['content'])

                if 'tool_calls' in message:
                    for tool in message['tool_calls']:
                        tool_call_map[tool['id']] = tool


def init_readline(session: Session, config: Config):
    if not sys.stdin.isatty():
        return

    home = Path.home()
    histfile = home / '.ok_history'

    readline.parse_and_bind(r'set completion-ignore-case on')
    readline.parse_and_bind(r'set enable-bracketed-paste on')

    readline.parse_and_bind(r"'\e[A': history-search-backward")
    readline.parse_and_bind(r"'\e[B': history-search-forward")

    readline.parse_and_bind(r"'\C-p': history-search-backward")
    readline.parse_and_bind(r"'\C-n': history-search-forward")

    try:
        readline.read_history_file(histfile)
        h_len = readline.get_current_history_length()
    except FileNotFoundError:
        histfile.touch()
        h_len = 0

    def save(prev_h_len, histfile):
        new_h_len = readline.get_current_history_length()
        readline.set_history_length(config.prompt_history_length)
        readline.append_history_file(new_h_len - prev_h_len, histfile)

    atexit.register(save, h_len, histfile)
    _init_completions(session, config)
