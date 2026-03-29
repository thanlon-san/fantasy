"""
Centralized logging configuration for fantasy football project
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Define log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> logging.Logger:
    """
    Create a configured logger

    Args:
        name: Logger name (usually __name__ of the module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        log_file = LOGS_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger
    """
    # Check if logger already exists and has handlers
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    return setup_logger(name)


# Pre-configured loggers for common modules
api_logger = setup_logger("api", level=logging.INFO)
recap_logger = setup_logger("recap_generator", level=logging.INFO)
trend_logger = setup_logger("trend_tracker", level=logging.INFO)
fetcher_logger = setup_logger("fetch_league_data", level=logging.INFO)


if __name__ == "__main__":
    # Test the logger
    test_logger = get_logger("test")

    test_logger.debug("This is a debug message")
    test_logger.info("✅ Logger is working correctly")
    test_logger.warning("This is a warning")
    test_logger.error("This is an error")

    print(f"\n📁 Logs are being written to: {LOGS_DIR.absolute()}")
    print(f"📄 Current log file: {datetime.now().strftime('%Y%m%d')}.log")
