import atexit
import readline
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from ok_agent.ansi_sequences import BOLD, RESET
from ok_agent.config import ConfigError, get_config
from ok_agent.llama_cpp.completions import completion
from ok_agent.llama_cpp.tools import handle_tool_call, tool_to_function_tool
from ok_agent.llama_cpp.types import AssistantMessage, Message
from ok_agent.llama_cpp.utils import get_models
from ok_agent.loggers import setup_logging
from ok_agent.tools.registry import create_registry, get_tools
from ok_agent.tools.types import Tool
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


def agent_loop(state: AppState, tools: list[Tool]):
    tool_registry = create_registry(tools)
    function_tools = [tool_to_function_tool(tool) for tool in tools]
    while True:
        try:
            query = input("\n> ").strip()

            if query.lower() == "exit":
                raise SystemExit

            if query.startswith("/model"):
                handle_model_command(state, query)
                continue

            if state.model is None:
                print("Please select a model with /model command")
                continue

            user_message: Message = {"role": "user", "content": query}
            state.messages.append(user_message)

            while response := completion(
                model=state.model,
                messages=state.messages,
                tools=function_tools,
            ):
                assistant_message: AssistantMessage = response["message"]
                finish_reason = response["finish_reason"]

                if (
                    "content" in assistant_message
                    or "tool_calls" in assistant_message
                ):
                    state.messages.append(assistant_message)
                else:
                    if finish_reason == "length":
                        print("Token generation limit exceeded.")
                    else:
                        print("The model did not produce any response")
                    break

                if "tool_calls" in assistant_message:
                    tool_results = [
                        handle_tool_call(tool_registry, tool_call)
                        for tool_call in assistant_message["tool_calls"]
                    ]

                    state.messages.extend(tool_results)

                match finish_reason:
                    case "length":
                        print("Token generation limit exceeded.")
                        break
                    case "stop":
                        break
                    case "tool_calls":
                        pass

        except KeyboardInterrupt:
            print("\nAgent Interrupted")
            continue


def cli():
    try:
        config = get_config()
    except ConfigError as e:
        print(f"{e.path}: {e.message}")
        raise SystemExit

    print(f"{BOLD}Ok Agent{RESET}")

    init_readline()
    init_completions()

    state = AppState(
        messages=[get_system_prompt()], models=[], model=config.model
    )

    agent_loop(state, tools=get_tools())


def main():
    setup_logging()
    try:
        cli()
    except (EOFError, SystemExit):
        print("\nExited")


if __name__ == "__main__":
    main()
