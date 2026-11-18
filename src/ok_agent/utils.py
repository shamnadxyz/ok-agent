import sys
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
from ok_agent.llama_cpp.types import Content

logger = getLogger(__name__)

type Style = Literal['ERROR', 'OK', 'WARNING', 'DIM', 'SPECIAL']


def format_text(
    text: str = '',
    style: Style | None = None,
    bold: bool = False,
):
    """Returns text formatted with ANSII escape sequences."""
    if not sys.stdout.isatty():
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


def content_to_text(content: Content) -> str:
    if isinstance(content, list):
        return ''.join(part['text'] for part in content if part['type'] == 'text')

    return content
