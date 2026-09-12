import sys

_isatty = sys.stdout.isatty()

BLACK_BG = "\033[40m" if _isatty else ""
BLUE_BRIGHT = "\033[94m" if _isatty else ""
BOLD = "\033[1m" if _isatty else ""
GREY = "\033[90m" if _isatty else ""
RED = "\033[91m" if _isatty else ""
WHITE = "\033[97m" if _isatty else ""
RESET = "\033[0m" if _isatty else ""
