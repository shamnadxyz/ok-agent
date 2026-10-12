import sqlite3
from pathlib import Path

from ok_agent.config import get_state_dir

INIT_COMMANDS = """
CREATE TABLE IF NOT EXISTS session_metadata(
    id INTEGER PRIMARY KEY,
    history_path TEXT NOT NULL,
    project_path TEXT NOT NULL,
    initial_query TEXT NOT NULL,
    model TEXT,
    created_at DATETIME NOT NULL
);
"""


def get_db_path() -> Path:
    state_dir = get_state_dir()
    return state_dir / "session.db"


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def get_db_connection() -> sqlite3.Connection:
    """Returns sqlite3 connection."""
    db_path = get_db_path()

    connection = sqlite3.connect(db_path)
    connection.row_factory = dict_factory

    with connection:
        connection.execute(INIT_COMMANDS)

    return connection
