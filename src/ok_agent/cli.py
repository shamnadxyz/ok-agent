import argparse
import atexit
import logging
import sqlite3
import termios
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError

from ok_agent.agent import LimitError, NoResponseError, get_system_prompt, run_agent
from ok_agent.commands import handle_commands
from ok_agent.config import Config, ConfigError, get_config
from ok_agent.llama_cpp.completions import CompletionError
from ok_agent.loggers import setup_logging
from ok_agent.session import (
    HistoryReadError,
    Session,
    find_session,
    find_sessions,
    get_previous_session,
    get_session_history_file,
    read_history_file,
    save_history,
)
from ok_agent.skills import get_skills
from ok_agent.temporary import temporary
from ok_agent.tools import (
    ToolNotFoundError,
    ToolRegistry,
)
from ok_agent.tools.display import HistoryMalformedError
from ok_agent.tools.edit_tool import edit_tool
from ok_agent.tools.read_tool import read_tool
from ok_agent.tools.shell_tool import shell_tool
from ok_agent.tools.write_tool import write_tool
from ok_agent.tui import disable_input, init_readline, replay_history
from ok_agent.utils import display_text

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='ok-agent', description='A minimal coding agent'
    )

    parser.add_argument('-m', '--model', metavar='MODEL_ID')
    parser.add_argument('--api-base-url')
    parser.add_argument(
        '--preserve-reasoning',
        action='store_true',
        help='Include reasoning in requests',
    )
    parser.add_argument('--api-key')
    parser.add_argument('-l', '--list-tools', action='store_true')
    parser.add_argument(
        '-T',
        '--tools',
        help="Tools to enable (eg: 'read,shell')",
    )

    parser.add_argument(
        '-t',
        '--max-turns',
        help='Maximum number of agent turns',
        type=int,
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '-r',
        '--resume',
        nargs='?',
        const=-1,
        type=int,
        metavar='SESSION_ID',
    )

    group.add_argument(
        '-L',
        '--list-history',
        help='List history with session_id and the initial query.',
        nargs='?',
        const='cwd',
        choices=['all', 'cwd'],
    )

    return parser.parse_args()


def apply_cli_overrides(config: Config, args: argparse.Namespace) -> None:
    if args.model is not None:
        config.model = args.model

    if args.api_base_url is not None:
        config.api_base_url = args.api_base_url

    if args.api_key is not None:
        config.api_key = args.api_key

    if args.preserve_reasoning:
        config.preserve_reasoning = args.preserve_reasoning

    if args.max_turns is not None:
        if args.max_turns <= 0:
            message = f"Ignoring max_turns: '{args.max_turns}'. max_turns must be a positive number."
            logger.warning(message)
            display_text(message, style='WARNING')
        else:
            config.max_turns = args.max_turns


def repl(
    session: Session,
    config: Config,
):
    init_readline(session, config)

    if not session.messages:
        session.messages.append(get_system_prompt(session.skills))

    atexit.register(save_history, session)

    while True:
        query = input(config.prompt).strip()

        if query.lower() == 'exit':
            raise SystemExit()

        if query == '':
            continue

        if query.startswith('/'):
            invoke_agent, query = handle_commands(
                query=query, session=session, config=config
            )
            if not invoke_agent:
                continue

        if session.model is None:
            display_text('Please select a model with /model command', 'WARNING')
            continue

        if session.initial_query is None and query is not None:
            session.initial_query = query

        try:
            with disable_input():
                run_agent(
                    query=query,
                    api_base_url=config.api_base_url,
                    api_key=config.api_key,
                    tool_registry=session.tool_registry,
                    model=session.model,
                    message_history=session.messages,
                    max_turns=config.max_turns,
                    preserve_reasoning=config.preserve_reasoning,
                    show_tool_result=config.show_tool_result,
                )

        except (LimitError, NoResponseError, CompletionError, URLError) as e:
            logger.error(e)
            display_text(str(e), 'ERROR')
        except KeyboardInterrupt:
            display_text('\nAgent Interrupted')
            continue


def app():
    args = parse_args()

    try:
        config = get_config()
    except ConfigError as e:
        display_text(f'{e.path}: {e}', 'ERROR')
        raise SystemExit(1)

    setup_logging(
        directory=config.log_directory,
        filename=config.log_filename,
        max_bytes=config.log_max_bytes,
        backup_count=config.log_backup_count,
        log_level=config.log_level,
    )

    if config.log_disable:
        logging.disable(logging.CRITICAL)

    apply_cli_overrides(config, args)

    tool_registry = ToolRegistry(
        [
            read_tool,
            write_tool,
            edit_tool,
            shell_tool,
        ]
    )

    if args.tools:
        tools = [tool.strip() for tool in args.tools.split(',')]
        try:
            tool_registry = ToolRegistry(
                [tool_registry.get_tool(tool) for tool in tools]
            )
        except ToolNotFoundError as e:
            logger.error(e)
            display_text(str(e), 'ERROR')
            raise SystemExit(1)

    if args.list_tools:
        display_text('\n'.join(tool_registry.get_tools()))
        return

    if args.list_history:
        try:
            history = find_sessions(find_in=args.list_history)
        except sqlite3.Error as e:
            logger.exception('Failed list history')
            display_text(str(e), style='ERROR')
            raise SystemExit(1)

        if not history:
            display_text('No history found')
            raise SystemExit(1)

        for entry in history:
            short_prompt = textwrap.shorten(
                entry['initial_query'], width=79, placeholder='...'
            )
            display_text(f'{entry["id"]}: {short_prompt}')
        return

    session = Session(
        history_path=get_session_history_file(),
        project_path=Path.cwd(),
        created_at=datetime.now(UTC),
        model=config.model,
        models=None,
        skills=get_skills(),
        tool_registry=tool_registry,
        messages=[],
    )

    if args.resume is not None:
        try:
            if args.resume == -1:
                prev_session = get_previous_session()
            else:
                prev_session = find_session(args.resume)
        except sqlite3.Error as e:
            logger.exception('Failed to resume')
            display_text(str(e), style='ERROR')
            raise SystemExit(1)

        if prev_session is None:
            display_text('Session not found')
            raise SystemExit(1)

        history_file = Path(prev_session['history_path'])

        try:
            session.messages = read_history_file(history_file)
        except HistoryReadError as e:
            logger.exception('Failed to read history')
            display_text(str(e), style='ERROR')
            raise SystemExit(1)

        session.history_path = history_file
        session.is_resume = True

        if args.model is None and (prev_model := prev_session.get('model')):
            session.model = prev_model

    display_text('Ok Agent', bold=True)

    if session.is_resume:
        try:
            replay_history(session.messages, tool_registry, config)
        except HistoryMalformedError as e:
            display_text(str(e), style='ERROR')
            raise SystemExit(1)

    atexit.register(temporary.remove_temp_files)
    try:
        repl(
            session=session,
            config=config,
        )
    except (EOFError, SystemExit, KeyboardInterrupt):
        display_text('\nExited')
    except termios.error as e:
        logger.exception('Termios error')
        display_text(str(e), style='ERROR')
        raise SystemExit(1)


if __name__ == '__main__':
    app()
