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
    Verifies that the logger.add method is called with the critical
    `enqueue=True` parameter to ensure asynchronous operation.
    """
    # Arrange
    mock_add = mocker.patch("loguru.logger.add")
    mocker.patch("loguru.logger.remove")  # Isolate from other tests

    # Act
    configure_logger("test-service", "testing")

    # Assert
    mock_add.assert_called_once()
    call_args, call_kwargs = mock_add.call_args
    assert call_kwargs.get("enqueue") is True, "Logging MUST be asynchronous"
    assert call_kwargs.get("serialize") is True, "Logging MUST be structured (JSON)"


@pytest.mark.parametrize(
    "environment, expected_backtrace, expected_diagnose",
    [
        ("production", False, False),
        ("staging", False, False),
        ("development", True, True),
        ("DEVELOPMENT", True, True),  # Test case-insensitivity
    ],
)
def test_production_safety_modes(mocker, environment, expected_backtrace, expected_diagnose):
    """
    Ensures that high-overhead diagnostics (`backtrace`, `diagnose`) are
    disabled in production environments to prevent performance degradation.
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


def test_output_is_valid_nested_orjson():
    """
    Performs an end-to-end validation of the log output format.

    It verifies that:
    1. The logger produces a message.
    2. The output is valid JSON.
    3. The structure matches the required nested format.
    4. Critical context fields (`service`, `environment`, `level`) are present.
    """
    # Arrange
    # Use an in-memory text stream as a sink to capture output
    sink = io.StringIO()
    logger.remove()  # Ensure a clean state
    sys.stdout = sink  # Redirect stdout to our sink for this test

    test_service = "validator-service"
    test_env = "validation"
    log_message = "This is a validation message."

    # Act
    try:
        configure_logger(test_service, test_env)
        # We must retrieve the logger instance to ensure we are using the one
        # that was just configured.
        log = logger.bind(request_id="abc-123")
        log.warning(log_message)
        logger.complete()  # Wait for the async queue to be processed
        output = sink.getvalue()
    finally:
        # IMPORTANT: Restore stdout to its original state
        sys.stdout = sys.__stdout__

    # Assert
    assert output, "Logger did not produce any output"

    # 1. The outer structure must be valid JSON from the patcher
    try:
        parsed_outer = orjson.loads(output)
    except orjson.JSONDecodeError as e:
        pytest.fail(f"Log output is not valid JSON. Error: {e}\nOutput:\n{output}")

    # 2. The outer JSON must contain a 'message' key holding the inner payload
    assert "message" in parsed_outer, "Outer JSON structure must have a 'message' key"
    inner_payload_str = parsed_outer["message"]

    # 3. The inner payload must also be valid JSON
    try:
        parsed_inner = orjson.loads(inner_payload_str)
    except orjson.JSONDecodeError as e:
        pytest.fail(f"Inner payload is not valid JSON. Error: {e}\nPayload:\n{inner_payload_str}")

    # 4. Verify the contents of the structured log
    assert parsed_inner.get("level") == "WARNING"
    assert parsed_inner.get("message") == log_message
    assert parsed_inner.get("service") == test_service
    assert parsed_inner.get("environment") == test_env
    assert parsed_inner.get("request_id") == "abc-123"  # Verify context binding
    assert "timestamp" in parsed_inner, "Timestamp must be present in the log"
