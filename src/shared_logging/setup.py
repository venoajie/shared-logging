# src/shared_logging/setup.py

import os
import sys

import orjson
from loguru import logger


def _orjson_serializer(record):
    """
    Custom serializer using orjson for high-performance JSON logging.
    This replaces Loguru's default serializer.
    """
    return orjson.dumps(record["extra"]).decode("utf-8")


def configure_logger(service_name: str, environment: str):
    """
    Configures the Loguru logger for standardized, high-performance,
    asynchronous, structured JSON output.

    This MUST be called once at the start of any service's main() function.
    """
    logger.remove()  # Remove any default or pre-existing handlers

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    is_development = environment.lower() == "development"

    # Core Configuration:
    # - sink: sys.stdout is the container standard for log collection.
    # - level: The minimum log level to process.
    # - format: "{message}" defers all formatting to the JSON serializer.
    # - serialize=True: Enables structured JSON logging.
    # - enqueue=True: CRITICAL. Moves logging to a background thread,
    #   decoupling application performance from I/O latency.
    # - backtrace/diagnose: Disabled in production to prevent performance hits.
    logger.add(
        sys.stdout,
        level=log_level,
        format="{message}",
        serialize=True,
        enqueue=True,  # Decouples application I/O from logging I/O.
        backtrace=is_development,  # Production safety.
        diagnose=is_development,  # Production safety.
    )

    # Bind the service context to all subsequent log messages.
    # This enriches every log entry with critical metadata for filtering.
    logger.configure(
        extra={"service": service_name, "environment": environment},
        patcher=lambda record: record.update(
            # Use orjson for serialization for performance gains.
            message=orjson.dumps(
                {
                    "timestamp": record["time"].isoformat(),
                    "level": record["level"].name,
                    "message": record["message"],
                    **record["extra"],
                }
            ).decode("utf-8")
        ),
    )

    logger.info(f"Asynchronous, structured JSON logger configured for '{service_name}'.")
