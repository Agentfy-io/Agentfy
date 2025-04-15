# -*- coding: utf-8 -*-
"""
@file: agentfy/common/utils/logging.py
@desc: Logging utility for the Agentfy backend.
@auth(s): Callmeiks
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(name, level=None):
    """
    Set up and return a configured logger

    Args:
        name (str): Name of the logger
        level (str, optional): Logging level. Options are 'debug', 'info', 'warning', 'error', 'critical'.
                               If not specified, it reads from the LOG_LEVEL environment variable, defaulting to 'info'.

    Returns:
        logging.Logger: Configured logger
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "info").upper()

    # Create the logger
    logger = logging.getLogger(name)

    # If the logger already has handlers, return it without reconfiguring
    if logger.handlers:
        return logger

    # Set logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create a console handler and set UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    # Handle Chinese characters in Windows console
    try:
        # Python 3.7+
        console_handler.stream.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older versions, set environment variable instead
        os.environ["PYTHONIOENCODING"] = "utf-8"

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create log directory
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create a rotating file handler (max 10MB per file, keep 10 backups), with UTF-8 encoding
    file_handler = RotatingFileHandler(
        log_dir / f"{name.replace('.', '_')}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'  # Explicitly set UTF-8 encoding
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Create the default logger
logger = setup_logger("agentfy_backend")
