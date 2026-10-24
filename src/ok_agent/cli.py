import argparse
import atexit
import json
import sqlite3
import textwrap
import time
from datetime import UTC, datetime
from logging import getLogger
from pathlib import Path

from ok_agent.agent import (
    Session,
    run_agent_loop,
)
from ok_agent.config import ConfigError, get_config, get_state_dir
from ok_agent.llama_cpp.types import Message, MessageToolCall
from ok_agent.loggers import setup_logging
from ok_agent.session import (
    find_session,
    find_sessions,
    get_previous_session,
)
from ok_agent.temporary import temporary
from ok_agent.tools import (
    TOOL_REGISTRY,
    ToolNotFoundError,
    ToolRegistry,
)
from ok_agent.tools.utils import format_tool_call
from ok_agent.utils import display_text, get_system_prompt

logger = getLogger(__name__)


class HistoryReadError(Exception):
    """Raises when fails to read history."""


def get_session_history_file() -> Path:
    """Returns a new session history file."""
    agent_dir = get_state_dir() / 'history'
    agent_dir.mkdir(exist_ok=True)
    time_ns = time.time_ns()
    date = datetime.now(UTC).strftime('%Y-%m-%d-%H-%M')
    filepath = agent_dir / f'{date} {time_ns}.jsonl'
    return filepath


def read_history_file(path: Path) -> list[Message]:
    """Returns message history from history file.

    Args:
        path: Path of the history file.
    Raises:
        HistoryReadError: if failed to read or parse history file.
    """
    messages: list[Message] = []
    try:
        with open(path) as f:
            for line in f:
                messages.append(json.loads(line.strip()))
            return messages
    except OSError as e:
        raise HistoryReadError(str(e))
    except json.JSONDecodeError as e:
        raise HistoryReadError(str(e))


def replay_history(messages: list[Message]):
    config = get_config()

    tool_call_map: dict[str, MessageToolCall] = {}

    for message in messages:
        match message['role']:
            case 'user':
                content = message['content']
                if isinstance(content, str):
                    display_text(f'{config.prompt_text}', 'SPECIAL', end='')
                    display_text(content)
                elif isinstance(content, list):
                    display_text(f'{config.prompt_text}', 'SPECIAL', end='')
                    for part in content:
                        if part['type'] == 'text':
                            display_text(part['text'], end='')

            case 'tool':
                tool_id = message['tool_call_id']
                tool_call = tool_call_map[tool_id]
                content = message['content']

                formatted_text = format_tool_call(
                    tool_call=tool_call,
                    state={'initialized': False, 'argument_states': {}},
                    is_final=True,
                )

                if formatted_text is None:
                    continue

                display_text(formatted_text, end='')
                if config.show_tool_result:
                    if isinstance(content, str):
                        display_text(content)
                    elif isinstance(content, list):
                        for part in content:
                            if part['type'] == 'text':
                                display_text(part['text'])

            case 'assistant':
                reasoning = message.get('reasoning_content')
                content = message.get('content')
                tool_calls: list = message.get('tool_calls', [])

                if reasoning:
                    display_text(reasoning, style='DIM')

                if isinstance(content, str):
                    display_text(content)

                if tool_calls:
                    for tool in tool_calls:
                        tool_call_map[tool['id']] = tool


def app():
    global TOOL_REGISTRY
    setup_logging()

    try:
        config = get_config()
        logger.debug(f'config: {config}')

    except ConfigError as e:
        display_text(f'{e.path}: {e.message}', 'ERROR')
        raise SystemExit(1)

    session = Session(
        history_path=get_session_history_file(),
        project_path=Path.cwd(),
        created_at=datetime.now(UTC),
        model=config.model,
        messages=[get_system_prompt()],
    )

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
        help=f'Maximum number of turns for the agent (default: {config.max_turns})',
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
        tools = [tool.strip() for tool in args.tools.split(',')]
        try:
            TOOL_REGISTRY = ToolRegistry(TOOL_REGISTRY.get_tools(tools))
        except ToolNotFoundError as e:
            message = f"tool '{e.name}' not found"
            logger.error(message)
            display_text(message, 'ERROR')
            raise SystemExit(1)

    if args.list_tools:
        for tool in TOOL_REGISTRY.get_tools():
            display_text(tool['name'])
        return

    if args.max_turns:
        config.max_turns = args.max_turns

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

    if args.resume:
        session.is_resume = True
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
            session.history_path = history_file
        except HistoryReadError as e:
            logger.exception('Failed to read history')
            display_text(str(e), style='ERROR')
            raise SystemExit(1)
        prev_model = prev_session.get('model')
        if prev_model:
            session.model = prev_model

    display_text('Ok Agent', bold=True)

    if session.is_resume:
        replay_history(session.messages)

    atexit.register(temporary.remove_temp_files)
    try:
        run_agent_loop(
            tool_registry=TOOL_REGISTRY,
            session=session,
        )
    except (EOFError, SystemExit, KeyboardInterrupt):
        display_text('\nExited')


if __name__ == '__main__':
    app()
