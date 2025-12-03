# src\shared_logging\config.py

import os
import sys

from loguru import logger


def configure_logger(service_name: str, environment: str):
    """
    Configures the Loguru logger for standardized, structured JSON output.
    This should be called once at the very start of a service's main() function.
    """
    logger.remove()  # Remove any default or pre-existing handlers

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Configure a single, correct handler that uses Loguru's native JSON serialization.
    # This configuration is efficient and avoids the cause of the KeyError.
    logger.add(
        sys.stdout,
        level=log_level,
        format="{message}",
        serialize=True,
        backtrace=True,
        diagnose=True,
    )

    # Bind the service context to all subsequent log messages.
    logger.configure(extra={"service": service_name, "environment": environment})

    logger.info(f"Structured JSON logger configured for '{service_name}'.")
