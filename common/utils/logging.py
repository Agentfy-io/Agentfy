# -*- coding: utf-8 -*-
"""
@file: agentfy/common/utils/logging.py
@desc: customized exceptions
@auth: Callmeiks
"""
import logging
import logging.config
import json
import os
from datetime import datetime


class CustomJsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Include exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Include custom fields
        if hasattr(record, 'data') and record.data:
            log_record.update(record.data)

        return json.dumps(log_record)


def setup_logging(log_level=None, log_file=None):
    """Configure logging with structured JSON format."""
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": CustomJsonFormatter
            },
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level or "INFO",
                "formatter": "standard" if os.getenv("HUMAN_READABLE_LOGS", "false").lower() == "true" else "json",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": log_level or "INFO",
                "propagate": True
            }
        }
    }

    # Add file handler if log file is specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level or "INFO",
            "formatter": "json",
            "filename": log_file,
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5
        }
        config["loggers"][""]["handlers"].append("file")

    logging.config.dictConfig(config)
    return logging.getLogger()


def get_logger(name):
    """Get a logger with the given name."""
    logger = logging.getLogger(name)

    # Add a method to log with extra data
    def log_with_data(level, msg, data=None, *args, **kwargs):
        if data:
            extra = kwargs.get("extra", {})
            extra["data"] = data
            kwargs["extra"] = extra
        logger.log(level, msg, *args, **kwargs)

    # Add convenience methods
    logger.debug_with_data = lambda msg, data=None, *args, **kwargs: log_with_data(logging.DEBUG, msg, data, *args,
                                                                                   **kwargs)
    logger.info_with_data = lambda msg, data=None, *args, **kwargs: log_with_data(logging.INFO, msg, data, *args,
                                                                                  **kwargs)
    logger.warning_with_data = lambda msg, data=None, *args, **kwargs: log_with_data(logging.WARNING, msg, data, *args,
                                                                                     **kwargs)
    logger.error_with_data = lambda msg, data=None, *args, **kwargs: log_with_data(logging.ERROR, msg, data, *args,
                                                                                   **kwargs)
    logger.critical_with_data = lambda msg, data=None, *args, **kwargs: log_with_data(logging.CRITICAL, msg, data,
                                                                                      *args, **kwargs)

    return logger