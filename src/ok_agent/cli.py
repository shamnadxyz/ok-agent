import atexit
import readline
from pathlib import Path

from ok_agent.ansi_sequences import BOLD, RESET
from ok_agent.config import get_system_prompt
from ok_agent.loggers import setup_logging
from ok_agent.openai.completions import completion
from ok_agent.openai.types import Message
from ok_agent.tools.edit_tool import edit_tool
from ok_agent.tools.read_tool import read_tool
from ok_agent.tools.shell_tool import shell_tool
from ok_agent.tools.utils import get_tools_schema, handle_tool_calls
from ok_agent.tools.write_tool import write_tool


def init_readline():
    home = Path.home()
    histfile = home / ".ok_history"
    history_length = 1000

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

    tool_schemas, tools = get_tools_schema(
        [shell_tool, read_tool, write_tool, edit_tool]
    )

    print(f"{BOLD}Ok Agent{RESET}")

    while True:
        query = input("\n> ")

        if query.lower() == "exit":
            raise SystemExit

        user_message: Message = {"role": "user", "content": query}
        messages.append(user_message)

        while True:
            result = completion(
                messages=messages, tools=tool_schemas, model="qwen3.6-35b-a3b"
            )
            # TODO: add stop reason handling

            if result is None:
                break

            assitant_message: Message = {
                "role": "assistant",
                **result,
            }

            messages.append(assitant_message)

            if "tool_calls" not in result:
                break

            tool_results = handle_tool_calls(tools, result["tool_calls"])
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
