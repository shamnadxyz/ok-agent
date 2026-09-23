import logging
from logging import Logger, getLogger
from logging.handlers import RotatingFileHandler

from ok_agent.config import get_config


def _create_rotating_logger(
    filename: str,
    name: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 2,
    level: int = logging.DEBUG,
    propagate: bool = True,
) -> Logger:
    config = get_config()
    logs_path = config["state_dir"] / "logs"

    logs_path.mkdir(exist_ok=True)

    logger = getLogger() if name is None else getLogger(name)

    handler = RotatingFileHandler(
        logs_path / filename,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )

    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = propagate

    return logger


def setup_logging():
    _create_rotating_logger(filename="app.log")
    _create_rotating_logger(
        filename="trace.jsonl", name="llm.traces", propagate=False
    )
