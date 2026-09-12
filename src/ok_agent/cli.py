from ok_agent.ansi_sequences import BOLD, RESET
from ok_agent.loggers import setup_logging
from ok_agent.openai.completions import completion
from ok_agent.openai.types import Message
from ok_agent.tools.edit_tool import edit_tool
from ok_agent.tools.read_tool import read_tool
from ok_agent.tools.shell_tool import shell_tool
from ok_agent.tools.utils import get_tools_schema, handle_tool_calls
from ok_agent.tools.write_tool import write_tool
from ok_agent.utils import get_system_prompt


def cli():
    messages: list[Message] = [get_system_prompt()]

    selected_tools = [shell_tool, read_tool, write_tool, edit_tool]
    tool_schemas, tools = get_tools_schema(selected_tools)

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
    try:
        cli()
    except (EOFError, KeyboardInterrupt, SystemExit):
        print("Exit")


if __name__ == "__main__":
    main()
