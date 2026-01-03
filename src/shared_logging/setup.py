# src/shared_logging/setup.py

import os
import sys

import orjson
from loguru import logger


def json_formatter(record: dict) -> str:
    """
    Formats a log record into a standardized, orjson-serialized JSON string.

    Args:
        record: The Loguru record dictionary.

    Returns:
        A JSON string representation of the log record, terminated with a newline.
    """
    log_object = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "extra": record["extra"],
    }
    # Cleanly merge the 'extra' dictionary into the top-level log object
    log_object.update(record["extra"])
    del log_object["extra"]  # Remove the redundant 'extra' key

    # Append exception details if they exist
    if record["exception"]:
        log_object["exception"] = str(record["exception"])

    return orjson.dumps(log_object).decode("utf-8") + "\n"


def configure_logger(service_name: str, environment: str):
    """
    Configures the Loguru logger for standardized, high-performance,
    asynchronous, structured JSON output.

    This MUST be called once at the start of any service's main() function.
    """
    logger.remove()

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    is_development = environment.lower() == "development"

    # Core Configuration:
    # - format: A custom function for full control over serialization.
    # - enqueue=True: CRITICAL. Moves logging to a background thread.
    # - backtrace/diagnose: Disabled in production for performance.
    logger.add(
        sys.stdout,
        level=log_level,
        format=json_formatter,
        enqueue=True,
        backtrace=is_development,
        diagnose=is_development,
    )

    # Bind the service context to all subsequent log messages.
    logger.configure(extra={"service": service_name, "environment": environment})

    logger.info(f"Asynchronous, structured JSON logger configured for '{service_name}'.")
