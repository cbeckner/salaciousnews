"""
Centralized logging configuration with ANSI color formatting.
"""

import logging

# ANSI escape sequences for colors
COLORS = {
    'DEBUG': '\033[94m',    # Blue
    'INFO': '\033[92m',     # Green
    'WARNING': '\033[93m',  # Yellow
    'ERROR': '\033[91m',    # Red
    'CRITICAL': '\033[95m', # Magenta
    'RESET': '\033[0m'      # Reset to default
}


class ColorFormatter(logging.Formatter):
    def format(self, record):
        log_color = COLORS.get(record.levelname, COLORS['RESET'])
        message = super().format(record)
        return f"{log_color}{message}{COLORS['RESET']}"


_configured = False


def setup_logging(level=logging.DEBUG):
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler()
        formatter = ColorFormatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        root.addHandler(handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
