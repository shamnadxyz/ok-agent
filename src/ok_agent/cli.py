import argparse
from copy import deepcopy
from logging import getLogger

from ok_agent.agent import (
    run_agent_loop,
)
from ok_agent.config import ConfigError, get_config
from ok_agent.loggers import setup_logging
from ok_agent.tools import (
    TOOL_REGISTRY,
    ToolNotFoundError,
    ToolRegistry,
)
from ok_agent.utils import display_text

logger = getLogger(__name__)


def app():
    setup_logging()

    try:
        config = get_config()
    except ConfigError as e:
        display_text(f"{e.path}: {e.message}", "ERROR")
        raise SystemExit()

    tool_registry = deepcopy(TOOL_REGISTRY)

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
            tool_registry = ToolRegistry(TOOL_REGISTRY.get_tools(tools))
        except ToolNotFoundError as e:
            message = f"tool '{e.name}' not found"
            logger.error(message)
            display_text(message, "ERROR")
            raise SystemExit

    if args.list_tools:
        for tool in tool_registry.get_tools():
            display_text(tool["name"])
        return

    if args.max_turns:
        config.max_turns = args.max_turns

    try:
        run_agent_loop(tool_registry)
    except (EOFError, SystemExit, KeyboardInterrupt):
        display_text("\nExited")


if __name__ == "__main__":
    app()
