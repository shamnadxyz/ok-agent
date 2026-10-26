from logging import getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    filename: str,
    max_bytes: int,
    backup_count: int,
    directory: str,
    log_level: int | str,
) -> None:
    """Setup logging.

    Args:
        filename: Log filename.
        max_bytes: Max size in bytes for a log file.
        backup_count: Number of log files to keep.
        directory: Directory path to store logs.
        log_level: Log level.
    """
    logs_dir = Path(directory).expanduser()
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = getLogger()

    if not logger.handlers:
        handler = RotatingFileHandler(
            logs_dir / filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )

        logger.addHandler(handler)

    logger.setLevel(log_level)
