import sys
from functools import lru_cache
from logging import getLogger
from typing import Literal

from ok_agent.ansi_sequences import (
    BOLD,
    BRIGHT_BLUE,
    BRIGHT_GRAY,
    BRIGHT_GREEN,
    BRIGHT_RED,
    BRIGHT_YELLOW,
    RESET,
)

logger = getLogger(__name__)

type Style = Literal['ERROR', 'OK', 'WARNING', 'DIM', 'SPECIAL']


@lru_cache(maxsize=1)
def _isatty():
    return sys.stdout.isatty()


def format_text(
    text: str = '',
    style: Style | None = None,
    bold: bool = False,
):
    """Returns text formatted with ANSII escape sequences."""
    if not _isatty():
        return text

    if bold:
        text = f'{BOLD}{text}{RESET}'

    if not style:
        return text

    match style:
        case 'DIM':
            text = f'{BRIGHT_GRAY}{text}{RESET}'
        case 'ERROR':
            text = f'{BRIGHT_RED}{text}{RESET}'
        case 'OK':
            text = f'{BRIGHT_GREEN}{text}{RESET}'
        case 'WARNING':
            text = f'{BRIGHT_YELLOW}{text}{RESET}'
        case 'SPECIAL':
            text = f'{BRIGHT_BLUE}{text}{RESET}'

    return text


def display_text(
    text: str = '',
    style: Style | None = None,
    bold: bool = False,
    end: str = '\n',
) -> None:
    """Displays text formatted with ANSII escape sequences."""
    if end:
        text = f'{text}{end}'

    if style or bold:
        text = format_text(text, style, bold)

    sys.stdout.write(text)
    sys.stdout.flush()


def clear_lines_above(count: int) -> None:
    """Clear lines above the current cursor.

    Args:
        count: number of lines to clear above the cursor.
    """
    for _ in range(count):
        sys.stdout.write('\033[1A')
        sys.stdout.write('\033[2K')
    sys.stdout.flush()
