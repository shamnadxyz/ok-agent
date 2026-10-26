import atexit
import readline
import sys
import termios
from logging import getLogger
from pathlib import Path
from urllib.error import URLError

from ok_agent.config import get_config
from ok_agent.llama_cpp.completions import (
    CompletionError,
    NoFinishReasonError,
    completion,
)
from ok_agent.llama_cpp.tools import (
    handle_tool_calls,
    tools_to_function_tools,
)
from ok_agent.llama_cpp.types import (
    Message,
)
from ok_agent.llama_cpp.utils import get_models
from ok_agent.session import Session, save_history
from ok_agent.tools import ToolRegistry
from ok_agent.utils import display_text

logger = getLogger(__name__)


class AgentError(Exception):
    """Common base class for all agent exceptions."""


class NoResponseError(AgentError):
    """Raises when the agent fails to produce a content response."""


class LimitError(AgentError):
    """Limit exceeded exceptions.

    Attributes:
        agent_response: The agent response from the last turn.
    """

    def __init__(
        self,
        message: str,
    ):
        super().__init__(message)


class TokenLimitError(LimitError):
    """Raises when the finish reason is length."""


class TurnLimitError(LimitError):
    """Raises when the maximum number of turns are exceeded.

    Attributes:
        agent_response: The agent response from the last turn.
    """

    def __init__(
        self,
        turn: int,
        turn_limit: int,
    ):
        self.turn = turn
        self.turn_limit = turn_limit

        super().__init__(
            f'Turn limit reached: {self.turn}/{self.turn_limit}',
        )


def init_completions():
    commands = ['/model', '/continue']
    model_completions = []

    def complete(text: str, state: int) -> str | None:
        completions = commands
        if text == '':
            return None

        if text.startswith('/model'):
            if not model_completions:
                model_completions.extend(get_model_completions())

            completions = model_completions

        candidates = [command for command in completions if command.startswith(text)]

        if state < len(candidates):
            return candidates[state]
        else:
            return None

    readline.parse_and_bind('tab: complete')
    readline.set_completer(complete)
    readline.set_completer_delims('')


def init_readline():
    home = Path.home()
    histfile = home / '.ok_history'
    config = get_config()
    prompt_history_length = config.prompt_history_length

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
        readline.set_history_length(prompt_history_length)
        readline.append_history_file(new_h_len - prev_h_len, histfile)

    atexit.register(save, h_len, histfile)


def get_model_completions() -> list[str]:
    return [f'/model {model}' for model in get_models()]


def handle_model_command(session: Session, query: str):
    models = get_models()

    selected_model = query.removeprefix('/model').strip()

    if selected_model == '':
        display_text('Please pass the model id')
        return

    if session.model == selected_model:
        return

    if selected_model not in models:
        display_text(f"model '{selected_model}' not found", 'ERROR')
        return

    session.model = selected_model
    display_text(f'Selected model: {selected_model}')


def agent(
    tool_registry: ToolRegistry,
    model: str,
    messages: list[Message],
    preserve_reasoning: bool,
    query: str | None = None,
    max_turns: int = 15,
) -> str:
    """Send query to the agent.

    Args:
        query: Query to send.
        tool_registry: Tool registry available to the agent.
        model: Model ID.
        messages: The agent's message history.
        preserve_reasoning: whether to send back the reasoning content.
        max_turns: The maximum number of turns.

    Returns:
        The agent's final response.

    Raises:
        CompletionError: if HTTPError occured
        NoResponseError: if agent did not produce a response.
        TurnLimitError: if the maximum number of turns are exceeded.
        TokenLimitError: if the maximum token limit is reached.
        URLError
    """
    function_tools = tools_to_function_tools(tool_registry)
    turn = 0

    message = None

    if query:
        user_message: Message = {'role': 'user', 'content': query}
        messages.append(user_message)

    kwargs = {
        'preserve_thinking': preserve_reasoning,
    }

    while turn < max_turns:
        try:
            response = completion(
                model=model,
                messages=messages,
                tools=function_tools,
                chat_template_kwargs=kwargs,
            )
            finish_reason = response['finish_reason']
        except NoFinishReasonError as e:
            raise CompletionError('finish_reason missing') from e

        assistant_response = response['message']

        # Store content response for returning as the final response
        if 'content' in assistant_response:
            message = assistant_response['content']

        if finish_reason == 'stop':
            if 'content' not in assistant_response:
                raise CompletionError('missing content')

            messages.append(assistant_response)
            break

        elif finish_reason == 'tool_calls':
            if 'tool_calls' not in assistant_response:
                raise CompletionError('missing tool_calls')

            messages.append(assistant_response)
            messages.extend(
                handle_tool_calls(
                    tool_registry=tool_registry,
                    tool_calls=assistant_response['tool_calls'],
                )
            )
        elif finish_reason == 'length':
            raise TokenLimitError(
                'Maximum token limit reached',
            )

        turn += 1

    if turn >= max_turns:
        raise TurnLimitError(
            turn=turn,
            turn_limit=max_turns,
        )

    if message is None:
        raise NoResponseError('Model failed to produce a response')

    return message


def run_agent_loop(tool_registry: ToolRegistry, session: Session):
    config = get_config()

    init_readline()
    init_completions()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    # Disable the ECHO attribute
    new[3] = new[3] & ~termios.ECHO

    atexit.register(save_history, session)

    while True:
        # Restore original terminal attributes
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

        # Discard queued data on STDIN
        termios.tcflush(fd, termios.TCIFLUSH)

        query = input(config.prompt).strip()

        if query.lower() == 'exit':
            raise SystemExit()

        if query == '':
            continue

        if query.startswith('/model'):
            handle_model_command(session, query)
            continue

        if session.model is None:
            display_text('Please select a model with /model command', 'WARNING')
            continue

        if query.strip() == '/continue':
            if len(session.messages) == 0:
                display_text('History empty', style='WARNING')
                continue

            previous_message = session.messages[-1]

            if previous_message['role'] in ['tool', 'user']:
                query = None
            else:
                query = 'continue'

        if session.initial_query is None and query is not None:
            session.initial_query = query

        try:
            # Set the attributes to disable echoing of typed characters
            termios.tcsetattr(fd, termios.TCSADRAIN, new)

            agent(
                query=query,
                tool_registry=tool_registry,
                model=session.model,
                messages=session.messages,
                max_turns=config.max_turns,
                preserve_reasoning=config.preserve_reasoning,
            )

        except LimitError as e:
            logger.error(e)
            display_text(str(e), 'ERROR')
        except NoResponseError as e:
            logger.error(e)
            display_text(str(e), 'ERROR')
        except CompletionError as e:
            logger.error(e)
            display_text(str(e), 'ERROR')
        except URLError as e:
            logger.error(e.reason)
            display_text(str(e.reason), 'ERROR')
        except KeyboardInterrupt:
            display_text('\nAgent Interrupted')
            continue
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
