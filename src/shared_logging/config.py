# src\shared_logging\config.py
import sys
import orjson
from loguru import logger

def configure_logger(service_name: str, environment: str):
    """
    Configures the Loguru logger for standardized, structured JSON output.
    This should be called once at the very start of a service's main() function.
    """
    logger.remove() # Remove the default handler

    def serialize(record):
        """Custom serializer to format log records as JSON."""
        subset = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "service": service_name,
            "environment": environment,
        }
        if record["extra"]:
            subset.update(record["extra"])
        if record["exception"]:
            # Handle exception formatting
            subset["exception"] = str(record["exception"])
        return orjson.dumps(subset).decode("utf-8")

    def formatter(record):
        """Pass-through formatter that adds a newline."""
        return serialize(record) + "\n"

    logger.add(
        sys.stdout,
        format=formatter,
        level="INFO",
        serialize=False # We handle serialization manually in the formatter
    )
    logger.info(f"Structured JSON logger configured for '{service_name}'.")
