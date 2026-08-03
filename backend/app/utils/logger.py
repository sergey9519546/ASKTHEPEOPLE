"""
Logging configuration module
Provides unified logging management, outputting to both console and file
"""

import os
import sys
import logging
import re
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler


def _ensure_utf8_stdout():
    """
    Ensure stdout/stderr use UTF-8 encoding
    Resolves Chinese character encoding issues in Windows console
    """
    if sys.platform == 'win32':
        # Reconfigure standard output to UTF-8 on Windows
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# Log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')


class _ProductionPrivacyFilter(logging.Filter):
    """Keep private prompts, provider payloads, and credentials out of logs."""

    _REDACTIONS = (
        (re.compile(r"(?i)(authorization:\s*bearer\s+)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{8,})\b"), "[REDACTED]"),
        (
            re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)\S+"),
            r"\1[REDACTED]",
        ),
        (
            re.compile(r"(?i)(://[^:/\s]+:)[^@\s]+@"),
            r"\1[REDACTED]@",
        ),
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if os.environ.get("FLASK_DEBUG", "False").lower() == "true":
            return True

        if record.levelno >= logging.WARNING and not getattr(
            record,
            "privacy_safe",
            False,
        ):
            record.msg = (
                f"{record.name}.{record.funcName}: event details suppressed "
                "by production logging policy"
            )
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            return True

        message = record.getMessage()
        for pattern, replacement in self._REDACTIONS:
            message = pattern.sub(replacement, message)
        record.msg = message
        record.args = ()
        return True


class JSONLogFormatter(logging.Formatter):
    """Structured JSON log formatter"""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt or '%Y-%m-%d %H:%M:%S'),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def _configured_level() -> int:
    """Return an operator-controlled level with safe production defaults."""
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    default_name = 'DEBUG' if debug_mode else 'INFO'
    level_name = os.environ.get('LOG_LEVEL', default_name).strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    # Production must not retain DEBUG records even if a stale deployment
    # variable asks for them.
    return level if debug_mode or level >= logging.INFO else logging.INFO


def setup_logger(name: str = 'askthepeople', level: int | None = None) -> logging.Logger:
    """
    Setup logger
    
    Args:
        name: Logger name
        level: Log level
        
    Returns:
        Configured logger
    """
    if level is None:
        level = _configured_level()

    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not any(
        isinstance(existing, _ProductionPrivacyFilter)
        for existing in logger.filters
    ):
        logger.addFilter(_ProductionPrivacyFilter())
    
    # Prevent logs from propagating to root logger to avoid duplicate output
    logger.propagate = False
    
    # Do not add if handler already exists
    if logger.handlers:
        return logger
    
    # Log format
    if os.environ.get('LOG_FORMAT', 'text').lower() == 'json':
        detailed_formatter = JSONLogFormatter()
        simple_formatter = JSONLogFormatter()
    else:
        detailed_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
    
    # 1. File handler - Detailed logs (named by date, with rotation)
    log_filename = datetime.now().strftime('%Y-%m-%d') + '.log'
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, log_filename),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    # Never retain DEBUG records by default in production.  Callers may opt
    # into another level through LOG_LEVEL, but the default follows
    # FLASK_DEBUG instead of silently writing verbose files in every mode.
    file_handler.setLevel(level)
    
    # 2. Console handler - Simple logs (INFO and above)
    # Ensure UTF-8 encoding on Windows to avoid encoding issues
    _ensure_utf8_stdout()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = 'askthepeople') -> logging.Logger:
    """
    Get logger (create if not exists)
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


# Create default logger
logger = setup_logger()


# Convenience methods
def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)

