import atexit
import readline
from pathlib import Path

from ok_agent.ansi_sequences import BOLD, RESET
from ok_agent.config import get_config, get_system_prompt
from ok_agent.loggers import setup_logging
from ok_agent.openai.completions import completion
from ok_agent.openai.tools import handle_tool_call, tool_to_function_tool
from ok_agent.openai.types import Message
from ok_agent.tools.registry import create_registry, get_tools


def init_readline():
    config = get_config()
    home = Path.home()
    histfile = home / ".ok_history"
    history_length = config["history_length"]

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


def cli():
    messages: list[Message] = [get_system_prompt()]

    tools = get_tools()
    tool_registry = create_registry(tools)
    function_tools = [tool_to_function_tool(tool) for tool in tools]

    print(f"{BOLD}Ok Agent{RESET}")

    while True:
        query = input("\n> ")

        if query.lower() == "exit":
            raise SystemExit

        user_message: Message = {"role": "user", "content": query}
        messages.append(user_message)

        while True:
            result = completion(
                messages=messages,
                tools=function_tools,
                model="qwen3.6-35b-a3b",
            )
            # TODO: add stop reason handling

            if result is None:
                break

            assistant_message: Message = {
                "role": "assistant",
                **result,
            }

            messages.append(assistant_message)

            if "tool_calls" not in result:
                break

            tool_results = [
                handle_tool_call(tool_registry, tool_call)
                for tool_call in result["tool_calls"]
            ]
            messages.extend(tool_results)


def main():
    setup_logging()
    init_readline()
    try:
        cli()
    except (EOFError, KeyboardInterrupt, SystemExit):
        print("Exit")


if __name__ == "__main__":
    main()
