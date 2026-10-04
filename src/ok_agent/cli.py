import argparse
import atexit
import readline
import sys
import termios
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from urllib.error import URLError

from ok_agent.agent import NoResponseError, TurnLimitExceededError, agent
from ok_agent.ansi_sequences import BOLD, RESET
from ok_agent.config import ConfigError, get_config
from ok_agent.llama_cpp.completions import CompletionError
from ok_agent.llama_cpp.types import Message
from ok_agent.llama_cpp.utils import get_models
from ok_agent.loggers import setup_logging
from ok_agent.tools import (
    ToolNotFoundError,
    ToolRegistry,
    edit_tool,
    read_tool,
    shell_tool,
    write_tool,
)
from ok_agent.utils import get_system_prompt

logger = getLogger(__name__)


@dataclass
class AppState:
    messages: list[Message]
    models: list[str]
    model: str | None


def get_model_completions() -> list[str]:
    return [f"/model {model}" for model in get_models()]


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


def handle_model_command(state: AppState, query: str):
    if not state.models:
        state.models = get_models()

    selected_model = query.removeprefix("/model").strip()

    if selected_model == "":
        print("Please pass the model id")
        return

    if state.model == selected_model:
        return

    if selected_model not in state.models:
        print(f"model '{selected_model}' not found")
        return

    state.model = selected_model
    print(f"Selected model: {selected_model}")


def cli(tool_registry: ToolRegistry):
    config = get_config()

    print(f"{BOLD}Ok Agent{RESET}")

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

        # Set the attributes to disable echoing of typed characters
        termios.tcsetattr(fd, termios.TCSADRAIN, new)

        if query.lower() == "exit":
            raise SystemExit()

        if query.startswith("/model"):
            handle_model_command(app_state, query)
            continue

        if app_state.model is None:
            print("Please select a model with /model command")
            continue

        try:
            agent(
                query=query,
                tools=tool_registry.get_tools(),
                model=app_state.model,
                messages=app_state.messages,
                max_turns=config.max_turns,
            )

        except CompletionError as e:
            logger.error(e.message)
            print(e.message)
        except NoResponseError as e:
            logger.error(e.message)
            print(e.message)
        except TurnLimitExceededError as e:
            logger.error(e.message)
            print(e.message)
        except URLError as e:
            logger.error(e.reason)
            print(e.reason)
        except KeyboardInterrupt:
            print("\nAgent Interrupted")
            continue
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    setup_logging()

    try:
        config = get_config()
    except ConfigError as e:
        print(f"{e.path}: {e.message}")
        raise SystemExit()

    tool_registry = ToolRegistry(
        [read_tool, write_tool, edit_tool, shell_tool]
    )

    parser = argparse.ArgumentParser(
        prog="ok-agent", description="A minimal coding agent"
    )

    parser.add_argument("-m", "--model", metavar="MODEL_ID")
    parser.add_argument("--api-base-url")
    parser.add_argument(
        "--preserve-reasoning",
        action="store_true",
        help="include reasoning in requests",
    )
    parser.add_argument("--api-key")
    parser.add_argument("-l", "--list-tools", action="store_true")
    parser.add_argument(
        "-T",
        "--tools",
        help="tools to enable (eg: 'read,shell')",
    )

    parser.add_argument(
        "-t",
        "--max-turns",
        help=f"Maximum number of turns for the agent (default: {config.max_turns})",
        type=int,
    )

    args = parser.parse_args()

    if args.model:
        config.model = args.model

    if args.api_base_url:
        config.api_base_url = args.api_base_url

    if args.api_key:
        config.api_key = args.api_key

    if args.preserve_reasoning:
        config.preserve_reasoning = args.preserve_reasoning

    if args.tools:
        tools = [tool.strip() for tool in args.tools.split(",")]
        try:
            tool_registry = ToolRegistry(tool_registry.get_tools(tools))
        except ToolNotFoundError as e:
            message = f"tool '{e.name}' not found"
            logger.error(message)
            print(message)

    if args.list_tools:
        for tool in tool_registry.get_tools():
            print(tool["name"])
        return

    if args.max_turns:
        config.max_turns = args.max_turns

    try:
        cli(tool_registry)
    except (EOFError, SystemExit):
        print("\nExited")


if __name__ == "__main__":
    main()
