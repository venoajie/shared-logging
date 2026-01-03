# tests/test_config.py

import io
import sys

import orjson
import pytest
from loguru import logger

# --- Module under test ---
from shared_logging.setup import configure_logger


def test_logger_is_correctly_configured(mocker):
    """
    Verifies that logger.add is called with `enqueue=True` for async operation.
    """
    # Arrange
    mock_add = mocker.patch("loguru.logger.add")
    mocker.patch("loguru.logger.remove")

    # Act
    configure_logger("test-service", "testing")

    # Assert
    mock_add.assert_called_once()
    _, call_kwargs = mock_add.call_args
    assert call_kwargs.get("enqueue") is True, "Logging MUST be asynchronous"


@pytest.mark.parametrize(
    "environment, expected_backtrace, expected_diagnose",
    [
        ("production", False, False),
        ("staging", False, False),
        ("development", True, True),
    ],
)
def test_production_safety_modes(mocker, environment, expected_backtrace, expected_diagnose):
    """
    Ensures that high-overhead diagnostics are disabled in production.
    """
    # Arrange
    mock_add = mocker.patch("loguru.logger.add")
    mocker.patch("loguru.logger.remove")

    # Act
    configure_logger("test-service", environment)

    # Assert
    mock_add.assert_called_once()
    _, call_kwargs = mock_add.call_args
    assert call_kwargs.get("backtrace") is expected_backtrace
    assert call_kwargs.get("diagnose") is expected_diagnose


def test_output_is_valid_json_and_contains_correct_data():
    """
    Performs an end-to-end validation of the log output format.

    It verifies that:
    1. The logger produces multiple lines of output.
    2. Each line is a self-contained, valid JSON object.
    3. The final log object contains the correct message and all bound context.
    """
    # Arrange
    sink = io.StringIO()
    logger.remove()
    sys.stdout = sink  # Redirect stdout to capture log output

    test_service = "validator-service"
    test_env = "validation"
    log_message = "This is a validation message."
    request_id = "abc-123"

    # Act
    try:
        configure_logger(test_service, test_env)
        log = logger.bind(request_id=request_id)
        log.warning(log_message)

        # Wait for the async queue to be fully processed before reading
        logger.complete()
        output = sink.getvalue()
    finally:
        # IMPORTANT: Restore stdout to its original state
        sys.stdout = sys.__stdout__
        logger.remove()  # Clean up handlers for subsequent tests

    # Assert
    assert output, "Logger did not produce any output"

    # Split the output into individual log lines, filtering out empty lines
    log_lines = [line for line in output.strip().split("\n") if line]
    assert len(log_lines) >= 2, "Expected at least two log entries (config + warning)"

    # We only care about the last log message, which is the one we triggered.
    last_log_line = log_lines[-1]

    try:
        parsed_log = orjson.loads(last_log_line)
    except orjson.JSONDecodeError as e:
        pytest.fail(f"The last log line is not valid JSON. Error: {e}\nLine:\n{last_log_line}")

    # Verify the contents of the structured log
    assert parsed_log.get("level") == "WARNING"
    assert parsed_log.get("message") == log_message
    assert parsed_log.get("service") == test_service
    assert parsed_log.get("environment") == test_env
    assert parsed_log.get("request_id") == request_id
    assert "timestamp" in parsed_log, "Timestamp must be present"
