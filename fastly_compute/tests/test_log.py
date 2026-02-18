"""Integration tests for Logging functionality."""

import json
import logging
import re

from fastly_compute.log import FastlyLogHandler, LogEndpoint
from fastly_compute.testing import AutoViceroyTestBase, on_viceroy


class TestLogging(AutoViceroyTestBase):
    """Logging integration tests."""

    VICEROY_CONFIG = {
        "local_server": {
            "log_endpoints": {
                "test-logs": {},
                "json-logs": {},
                "api-logs": {},
                "worker-logs": {},
                "default-logs": {},
            }
        }
    }

    def _get_logs_for_endpoint(self, endpoint_name):
        """Get all log messages for a specific endpoint from viceroy output.

        Args:
            endpoint_name: Name of the log endpoint

        Returns:
            List of log messages (without the endpoint prefix)
        """
        log_prefix = f"{endpoint_name} :: "
        logs = []
        for line in self.server().output_lines:
            if log_prefix in line:
                log_message = line.split(log_prefix, 1)[1]
                logs.append(log_message)
        return logs

    def assert_log_message(self, endpoint_name, expected_message):
        """Assert that an exact log message was written to viceroy stdout.

        Args:
            endpoint_name: Name of the log endpoint
            expected_message: Exact message expected
        """
        logs = self._get_logs_for_endpoint(endpoint_name)

        if expected_message in logs:
            return  # Found it!

        # Not found - provide helpful error message
        error_msg = (
            f"Expected exact log message not found.\n"
            f"Expected: {expected_message}\n"
            f"Actual logs for {endpoint_name}:\n  "
            + ("\n  ".join(logs) if logs else "(no logs)")
        )
        raise AssertionError(error_msg)

    def assert_log_matches(self, endpoint_name, pattern):
        """Assert that a log message matching the pattern was written to viceroy stdout.

        Args:
            endpoint_name: Name of the log endpoint
            pattern: Regex pattern to match
        """
        logs = self._get_logs_for_endpoint(endpoint_name)

        for log_message in logs:
            if re.search(pattern, log_message):
                return  # Found it!

        # Not found - provide helpful error message
        error_msg = (
            f"Expected log pattern not found.\n"
            f"Pattern: {pattern}\n"
            f"Actual logs for {endpoint_name}:\n  "
            + ("\n  ".join(logs) if logs else "(no logs)")
        )
        raise AssertionError(error_msg)

    def assert_log_count(self, endpoint_name, expected_count, pattern=None):
        """Assert that a specific number of log messages were written.

        Args:
            endpoint_name: Name of the log endpoint
            expected_count: Expected number of log messages
            pattern: Optional regex pattern to filter logs
        """
        logs = self._get_logs_for_endpoint(endpoint_name)

        if pattern:
            matching_logs = [log for log in logs if re.search(pattern, log)]
            actual_count = len(matching_logs)
            if actual_count == expected_count:
                return  # Success

            error_msg = (
                f"Expected {expected_count} log messages matching pattern, "
                f"found {actual_count}.\n"
                f"Pattern: {pattern}\n"
                f"Matching logs:\n  "
                + ("\n  ".join(matching_logs) if matching_logs else "(no matches)")
            )
        else:
            actual_count = len(logs)
            if actual_count == expected_count:
                return  # Success

            error_msg = (
                f"Expected {expected_count} log messages, found {actual_count}.\n"
                f"All logs for {endpoint_name}:\n  "
                + ("\n  ".join(logs) if logs else "(no logs)")
            )

        raise AssertionError(error_msg)

    # Writing messages

    @on_viceroy
    def log(cls, endpoint_name, message):
        """Log a message to a named endpoint."""
        endpoint = LogEndpoint.open(endpoint_name)
        endpoint.write(message)

    def test_write_string(self):
        """Test writing a string message."""
        self.log("test-logs", "Hello World")
        self.assert_log_message("test-logs", "Hello World")

    @on_viceroy
    def log_bytes(cls, endpoint_name):
        """Log a message to a named endpoint."""
        endpoint = LogEndpoint.open(endpoint_name)
        endpoint.write(b"Binary log data: \x00\x01\x02\x03")

    def test_write_bytes(self):
        """Test writing raw bytes, including null ones."""
        self.log_bytes("test-logs")
        self.assert_log_matches("test-logs", r"Binary log data")

    def test_write_unicode(self):
        """Test writing unicode characters."""
        message = "Hello 世界 🌍"
        self.log("test-logs", message)
        self.assert_log_message("test-logs", message)

    def test_write_empty_string(self):
        """Test writing an empty string (produces no log event per spec)."""
        self.log("test-logs", "")
        # Per spec: "Each call to write with a non-empty message produces a single log event"
        # Empty string shouldn't produce a log, but we can't easily verify this
        # since we share the endpoint with other tests. Just verify the API succeeds.

    @on_viceroy
    def log_with_context_manager(cls, endpoint_name):
        """Test using endpoint as a context manager."""
        with LogEndpoint.open(endpoint_name) as endpoint:
            endpoint.write("Message from context manager")

    def test_context_manager(self):
        """Test using endpoint as a context manager."""
        self.log_with_context_manager("test-logs")
        self.assert_log_message("test-logs", "Message from context manager")

    # Python logging integration

    @on_viceroy
    def log_at_level(cls, endpoint_name: str, level: str, message: str):
        """Log a message using Python logging stdlib integration."""
        logger = logging.getLogger(f"test_{endpoint_name}")
        logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        logger.handlers.clear()

        # Add Fastly handler with new API
        handler = FastlyLogHandler(default_endpoint=endpoint_name)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

        # Log at the requested level
        log_func = getattr(logger, level.lower())
        log_func(message)

        # Clean up
        handler.close()

    def test_standard_logging_integration(self):
        """Test integration with Python standard logging."""
        self.log_at_level("test-logs", "INFO", "Test message")
        # The log should include timestamp, logger name, level, and message
        self.assert_log_matches("test-logs", r"INFO.*Test message")

    @on_viceroy
    def log_with_extra(cls, endpoint_name):
        """Test logging with extra fields."""
        logger = logging.getLogger(f"test_extra_{endpoint_name}")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        handler = FastlyLogHandler(default_endpoint=endpoint_name)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s - user=%(user_id)s"
            )
        )
        logger.addHandler(handler)

        logger.info("User action", extra={"user_id": 12345})

        handler.close()

    def test_logging_with_extra_fields(self):
        """Test logging with extra fields."""
        self.log_with_extra("test-logs")
        # Should include the user_id in the formatted message
        self.assert_log_matches("test-logs", r"user=12345")

    @on_viceroy
    def log_multiple(cls, endpoint_name):
        """Test logging multiple messages."""
        logger = logging.getLogger(f"test_multiple_{endpoint_name}")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        handler = FastlyLogHandler(default_endpoint=endpoint_name)
        logger.addHandler(handler)

        count = 5
        for i in range(count):
            logger.info(f"Log message {i + 1}")

        handler.close()

    def test_logging_multiple_messages(self):
        """Test logging multiple messages in sequence."""
        self.log_multiple("test-logs")
        # Should have exactly 5 log messages with "Log message" in them
        self.assert_log_count("test-logs", 5, pattern=r"Log message")

    def test_logging_all_levels(self):
        """Test logging at all standard levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            self.log_at_level("test-logs", level, f"Test at {level}")
            self.assert_log_matches("test-logs", rf"{level}.*Test at {level}")

    @on_viceroy
    def log_json(cls, endpoint_name):
        """Test structured JSON logging."""
        logger = logging.getLogger(f"test_json_{endpoint_name}")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        handler = FastlyLogHandler(default_endpoint=endpoint_name)
        logger.addHandler(handler)

        # Create structured log message
        log_data = {
            "event": "request_processed",
            "status": 200,
            "duration_ms": 42,
            "user_id": 12345,
            "path": "/api/data",
        }
        logger.info(json.dumps(log_data))

        handler.close()

    def test_json_structured_logging(self):
        """Test structured logging with JSON format."""
        self.log_json("json-logs")
        # Should contain JSON with the expected fields
        self.assert_log_matches("json-logs", r'"event":\s*"request_processed"')
        self.assert_log_matches("json-logs", r'"user_id":\s*12345')

    # Endpoint routing tests

    @on_viceroy
    def log_with_mapper(cls, logger_name, level, message):
        """Test logging with endpoint mapper function."""
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        # Define a mapper that routes based on logger name
        def endpoint_mapper(name: str) -> str | None:
            if name.startswith("api"):
                return "api-logs"
            # Return None to use default
            return None

        handler = FastlyLogHandler(
            default_endpoint="default-logs", endpoint_mapper=endpoint_mapper
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

        # Log at the requested level
        log_func = getattr(logger, level.lower())
        log_func(message)

        handler.close()

    def test_logging_with_mapper_function(self):
        """Test endpoint routing using a mapper function."""
        self.log_with_mapper("api.requests", "INFO", "API request")
        # Should route to api-logs based on logger name
        self.assert_log_matches("api-logs", r"INFO.*API request")

    def test_logging_with_mapper_fallback(self):
        """Test endpoint routing with mapper fallback to default."""
        self.log_with_mapper("unknown", "INFO", "Unknown logger")
        # Should fall back to default-logs
        self.assert_log_matches("default-logs", r"INFO.*Unknown logger")

    @on_viceroy
    def log_with_dict(cls, logger_name, level, message):
        """Test logging with dict-based endpoint mapper."""
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        # Use a dict for simple mapping
        endpoint_map = {
            "api": "api-logs",
            "worker": "worker-logs",
            "background": "worker-logs",
        }

        handler = FastlyLogHandler(
            default_endpoint="default-logs",
            endpoint_mapper=lambda name: endpoint_map.get(name.split(".")[0]),
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

        # Log at the requested level
        log_func = getattr(logger, level.lower())
        log_func(message)

        handler.close()

    def test_logging_with_dict_mapper(self):
        """Test endpoint routing using a dict-based mapper."""
        self.log_with_dict("worker", "INFO", "Worker task")
        # Should route to worker-logs via dict lookup
        self.assert_log_matches("worker-logs", r"INFO.*Worker task")
