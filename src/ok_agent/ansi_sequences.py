import sys

_isatty = sys.stdout.isatty()

BOLD = "\033[1m" if _isatty else ""
BRIGHT_BLUE = "\033[94m" if _isatty else ""
BRIGHT_GRAY = "\033[90m" if _isatty else ""
BRIGHT_WHITE = "\033[97m" if _isatty else ""
GRAY = "\033[30m" if _isatty else ""
GRAY_BG = "\033[40m" if _isatty else ""
GREEN = "\033[32m" if _isatty else ""
GREEN_BG = "\033[42m" if _isatty else ""
RED = "\033[31m" if _isatty else ""
RED_BG = "\033[41m" if _isatty else ""
RESET = "\033[0m" if _isatty else ""
WHITE = "\033[37m" if _isatty else ""
YELLOW = "\033[33m" if _isatty else ""
