import atexit
import readline
import sys
import termios
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import cast
from urllib.error import URLError

from ok_agent.config import get_config
from ok_agent.llama_cpp.completions import (
    CompletionError,
    NoFinishReasonError,
    completion,
)
from ok_agent.llama_cpp.tools import (
    handle_tool_calls,
    tool_to_function_tool,
)
from ok_agent.llama_cpp.types import (
    AssistantMessage,
    Message,
)
from ok_agent.llama_cpp.utils import get_models
from ok_agent.tools import Tool, ToolRegistry
from ok_agent.utils import display_text, get_system_prompt

logger = getLogger(__name__)


@dataclass
class AppState:
    messages: list[Message]
    models: list[str]
    model: str | None


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
        agent_response: str | None = None,
    ):
        super().__init__(message)
        self.agent_response = agent_response


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
        agent_response: str | None = None,
    ):
        self.turn = turn
        self.turn_limit = turn_limit

        super().__init__(
            f"Turn limit reached: {self.turn}/{self.turn_limit}",
            agent_response=agent_response,
        )


def init_completions():
    commands = ["/model"]
    model_completions = []

    def complete(text: str, state: int) -> str | None:
        completions = commands
        if text == "":
            return None

        if text.startswith("/model"):
            if not model_completions:
                model_completions.extend(get_model_completions())

            completions = model_completions

        candidates = [
            command for command in completions if command.startswith(text)
        ]

        if state < len(candidates):
            return candidates[state]
        else:
            return None

    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)
    readline.set_completer_delims("")


def init_readline():
    home = Path.home()
    histfile = home / ".ok_history"
    config = get_config()
    history_length = config.history_length

    readline.parse_and_bind(r"set completion-ignore-case on")
    readline.parse_and_bind(r"set enable-bracketed-paste on")

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
        readline.set_history_length(history_length)
        readline.append_history_file(new_h_len - prev_h_len, histfile)

    atexit.register(save, h_len, histfile)


def get_model_completions() -> list[str]:
    return [f"/model {model}" for model in get_models()]


def handle_model_command(state: AppState, query: str):
    if not state.models:
        state.models = get_models()

    selected_model = query.removeprefix("/model").strip()

    if selected_model == "":
        display_text("Please pass the model id")
        return

    if state.model == selected_model:
        return

    if selected_model not in state.models:
        display_text(f"model '{selected_model}' not found", "ERROR")
        return

    state.model = selected_model
    display_text(f"Selected model: {selected_model}")


def agent(
    query: str,
    tools: list[Tool],
    model: str,
    messages: list[Message],
    max_turns: int = 15,
) -> str:
    """Send query to the agent.

    Args:
        query: Query to send.
        tools: List of available tools to the agent.
        model: Model ID.
        messages: The agent's message history.
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

    tool_registry = ToolRegistry(tools)
    function_tools = [tool_to_function_tool(tool) for tool in tools]
    turn = 0

    message = None

    user_message: Message = {"role": "user", "content": query}
    messages.append(user_message)

    while turn < max_turns:
        try:
            response = completion(
                model=model,
                messages=messages,
                tools=function_tools,
            )
            finish_reason = response["finish_reason"]
        except NoFinishReasonError as e:
            response = e.response
            finish_reason = None
        except CompletionError:
            raise
        except URLError:
            raise

        assistant_response = response["message"]

        # Store content response for returning as the final response
        if "content" in assistant_response:
            message = assistant_response["content"]

        if (
            "content" in assistant_response
            or "tool_calls" in assistant_response
        ):
            messages.append(cast(AssistantMessage, assistant_response))
        else:
            raise NoResponseError()

        if "tool_calls" in assistant_response:
            messages.extend(
                handle_tool_calls(
                    tool_registry=tool_registry,
                    tool_calls=assistant_response["tool_calls"],
                )
            )

        match finish_reason:
            case "length":
                raise TokenLimitError(
                    "Maximum token limit reached", agent_response=message
                )
            case "stop":
                break
            case "tool_calls":
                pass
            case None:
                break
        turn += 1

    if turn >= max_turns:
        raise TurnLimitError(
            turn=turn,
            turn_limit=max_turns,
            agent_response=message,
        )

    if message is None:
        raise NoResponseError()

    return message


def run_agent_loop(tool_registry: ToolRegistry):
    config = get_config()

    display_text("Ok Agent", bold=True)

    init_readline()
    init_completions()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    # Disable the ECHO attribute
    new[3] = new[3] & ~termios.ECHO

    app_state = AppState(
        model=config.model, models=[], messages=[get_system_prompt()]
    )

    while True:
        # Restore original terminal attributes
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

        query = input(config.prompt_text).strip()

        if query.lower() == "exit":
            raise SystemExit()

        if query.startswith("/model"):
            handle_model_command(app_state, query)
            continue

        if app_state.model is None:
            display_text(
                "Please select a model with /model command", "WARNING"
            )
            continue

        try:
            # Set the attributes to disable echoing of typed characters
            termios.tcsetattr(fd, termios.TCSADRAIN, new)

            agent(
                query=query,
                tools=tool_registry.get_tools(),
                model=app_state.model,
                messages=app_state.messages,
                max_turns=config.max_turns,
            )

        except LimitError as e:
            logger.error(e)
            display_text(str(e), "ERROR")
        except NoResponseError as e:
            logger.error(e)
            display_text(str(e), "ERROR")
        except CompletionError as e:
            logger.error(e)
            display_text(str(e), "ERROR")
        except URLError as e:
            logger.error(e.reason)
            display_text(str(e.reason), "ERROR")
        except KeyboardInterrupt:
            display_text("\nAgent Interrupted")
            continue
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
