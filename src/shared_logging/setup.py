# src/shared_logging/setup.py

import os
import sys

import orjson
from loguru import logger


def _json_patcher(record: dict) -> dict:
    """
    A Loguru patcher that transforms the log record's message into a
    structured JSON string. It flattens the 'extra' dictionary into the
    top level of the JSON payload.
    """
    # Start with the basic log structure
    log_json = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
    }
    # Merge the 'extra' dict (service, environment, bound context)
    # into the top level of the JSON object.
    log_json.update(record["extra"])

    # Serialize the entire object into a single JSON string and
    # replace the original message with it.
    record["message"] = orjson.dumps(log_json).decode("utf-8")
    return record


def configure_logger(service_name: str, environment: str):
    """
    Configures the Loguru logger for standardized, high-performance,
    asynchronous, structured JSON output.

    This MUST be called once at the start of any service's main() function.
    """
    logger.remove()  # Remove any default or pre-existing handlers

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    is_development = environment.lower() == "development"

    # 1. Configure the patcher to run for all loggers.
    # This transforms the record's data before it reaches any sink.
    logger.configure(
        extra={"service": service_name, "environment": environment},
        patcher=_json_patcher,
    )

    # 2. Add the sink.
    # Its only job is to print the (now JSON-formatted) message.
    logger.add(
        sys.stdout,
        level=log_level,
        format="{message}",  # The message is now a JSON string.
        enqueue=True,
        backtrace=is_development,
        diagnose=is_development,
    )

    logger.info(f"Asynchronous, structured JSON logger configured for '{service_name}'.")
