import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Literal, TypedDict

from ok_agent.db import get_db_connection
from ok_agent.llama_cpp.types import Message
from ok_agent.utils import display_text

logger = getLogger(__name__)


@dataclass
class Session:
    history_path: Path
    project_path: Path
    created_at: datetime
    messages: list[Message]
    model: str | None
    initial_query: str | None = None
    is_resume: bool = False


class SessionMetadata(TypedDict):
    id: int
    history_path: str
    project_path: str
    created_at: str
    model: str | None
    initial_query: str


def _save_session(session: Session) -> None:
    connection = get_db_connection()
    query = """
    INSERT INTO session_metadata(history_path, project_path, initial_query, model, created_at)
    VALUES (?, ?, ?, ?, ?);
    """

    try:
        with closing(connection) as con, con:
            con.execute(
                query,
                (
                    str(session.history_path),
                    str(session.project_path),
                    session.initial_query,
                    session.model,
                    session.created_at,
                ),
            )
    except sqlite3.Error as e:
        logger.exception('Error while saving session')
        display_text(str(e), style='ERROR')


def save_history(session: Session) -> None:
    """Save message history to file.

    Args:
        messages: Message history.
        path: Path for the history file.
    """
    if len(session.messages) <= 1:
        logger.info('Skipping save history: history empty or system prompt only')
        return
    if session.initial_query is None:
        logger.info('Skipping save history: missing initial query')
        return

    messages_jsonl = [json.dumps(message) for message in session.messages]
    session.history_path.write_text('\n'.join(messages_jsonl), encoding='utf-8')

    if not session.is_resume:
        _save_session(session)


def find_sessions(
    find_in: Literal['all', 'cwd'] = 'cwd',
) -> list[SessionMetadata]:
    connection = get_db_connection()

    with closing(connection) as con, con:
        if find_in == 'all':
            cursor = con.execute("""
                SELECT *
                FROM session_metadata;
                """)
            sessions = cursor.fetchall()
        elif find_in == 'cwd':
            cwd = str(Path.cwd())
            cursor = con.execute(
                """
                SELECT *
                FROM session_metadata
                WHERE project_path = ?
                ORDER BY created_at;
                """,
                (cwd,),
            )
            sessions = cursor.fetchall()
        return sessions


def find_session(id: int) -> SessionMetadata | None:
    """Find session metadata by id."""
    connection = get_db_connection()

    with closing(connection) as con, con:
        cursor = con.execute(
            """
                SELECT *
                FROM session_metadata
                WHERE id = ?;
                """,
            (id,),
        )
        return cursor.fetchone()


def get_previous_session() -> SessionMetadata | None:
    """Returns the previous session."""
    connection = get_db_connection()
    cwd = str(Path.cwd().resolve())

    with closing(connection) as con, con:
        cursor = con.execute(
            """
            SELECT *
            FROM session_metadata
            WHERE project_path = ?
            ORDER BY created_at DESC
            LIMIT 1;
            """,
            (cwd,),
        )
        return cursor.fetchone()
