"""Integration tests for Logging functionality."""

import re

from fastly_compute.testing import ViceroyTestBase


class TestLogging(ViceroyTestBase):
    """Logging integration tests."""

    WASM_FILE = "build/logging.composed.wasm"

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

    def assert_success(self, response, expected_data=None):
        """Assert that the response was successful.

        Args:
            response: The HTTP response
            expected_data: Optional dict of expected response data
        """
        assert response.status_code == 200
        data = response.json()
        if expected_data:
            for key, value in expected_data.items():
                assert data[key] == value
        return data

    def assert_error(self, response, error_type):
        """Assert that the response contains an error of the expected type.

        Args:
            response: The HTTP response
            error_type: Expected error type name (e.g., "LogEndpointInvalidNameError")
        """
        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == error_type

    def _get_logs_for_endpoint(self, endpoint_name):
        """Get all log messages for a specific endpoint from viceroy output.

        Args:
            endpoint_name: Name of the log endpoint

        Returns:
            List of log messages (without the endpoint prefix)
        """
        log_prefix = f"{endpoint_name} :: "
        logs = []
        for line in self.server.output_lines:
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

    def test_write_string(self):
        """Test writing a string message."""
        response = self.get("/test/write/test-logs/Hello%20World")
        self.assert_success(response, {"written": True})
        self.assert_log_message("test-logs", "Hello%20World")

    def test_write_bytes(self):
        """Test writing bytes directly."""
        response = self.get("/test/write-bytes/test-logs")
        self.assert_success(response, {"written": True})
        # Binary data with null bytes - verify at least one log was written
        self.assert_log_matches("test-logs", r"Binary log data")

    def test_write_unicode(self):
        """Test writing unicode characters."""
        response = self.get(
            "/test/write/test-logs/Hello%20%E4%B8%96%E7%95%8C%20%F0%9F%8C%8D"
        )
        self.assert_success(response, {"written": True})
        self.assert_log_message(
            "test-logs", "Hello%20%E4%B8%96%E7%95%8C%20%F0%9F%8C%8D"
        )

    def test_write_empty_string(self):
        """Test writing an empty string (produces no log event per spec)."""
        response = self.get("/test/write-empty/test-logs")
        self.assert_success(response, {"written": True})
        # Per spec: "Each call to write with a non-empty message produces a single log event"
        # Empty string shouldn't produce a log, but we can't easily verify this
        # since we share the endpoint with other tests. Just verify the API succeeds.

    def test_context_manager(self):
        """Test using endpoint as a context manager."""
        response = self.get("/test/context-manager/test-logs")
        self.assert_success(response, {"success": True})
        self.assert_log_message("test-logs", "Message from context manager")

    # Python logging integration

    def test_standard_logging_integration(self):
        """Test integration with Python standard logging."""
        response = self.get("/test/logging/test-logs/INFO/Test%20message")
        self.assert_success(response, {"logged": True})
        # The log should include timestamp, logger name, level, and message
        self.assert_log_matches("test-logs", r"INFO.*Test%20message")

    def test_logging_with_extra_fields(self):
        """Test logging with extra fields."""
        response = self.get("/test/logging-extra/test-logs")
        self.assert_success(response, {"logged": True})
        # Should include the user_id in the formatted message
        self.assert_log_matches("test-logs", r"user=12345")

    def test_logging_multiple_messages(self):
        """Test logging multiple messages in sequence."""
        response = self.get("/test/logging-multiple/test-logs")
        self.assert_success(response, {"count": 5})
        # Should have exactly 5 log messages with "Log message" in them
        self.assert_log_count("test-logs", 5, pattern=r"Log message")

    def test_logging_all_levels(self):
        """Test logging at all standard levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            response = self.get(f"/test/logging/test-logs/{level}/Test%20at%20{level}")
            self.assert_success(response, {"logged": True})
            self.assert_log_matches("test-logs", rf"{level}.*Test%20at%20{level}")

    def test_json_structured_logging(self):
        """Test structured logging with JSON format."""
        response = self.get("/test/json-log/json-logs")
        self.assert_success(response, {"logged": True})
        # Should contain JSON with the expected fields
        self.assert_log_matches("json-logs", r'"event":\s*"request_processed"')
        self.assert_log_matches("json-logs", r'"user_id":\s*12345')

    # Endpoint routing tests

    def test_logging_with_mapper_function(self):
        """Test endpoint routing using a mapper function."""
        response = self.get("/test/logging-with-mapper/api.requests/INFO/API%20request")
        self.assert_success(response, {"logged": True})
        # Should route to api-logs based on logger name
        self.assert_log_matches("api-logs", r"INFO.*API%20request")

    def test_logging_with_mapper_fallback(self):
        """Test endpoint routing with mapper fallback to default."""
        response = self.get("/test/logging-with-mapper/unknown/INFO/Unknown%20logger")
        self.assert_success(response, {"logged": True})
        # Should fall back to default-logs
        self.assert_log_matches("default-logs", r"INFO.*Unknown%20logger")

    def test_logging_with_dict_mapper(self):
        """Test endpoint routing using a dict-based mapper."""
        response = self.get("/test/logging-with-dict/worker/INFO/Worker%20task")
        self.assert_success(response, {"logged": True})
        # Should route to worker-logs via dict lookup
        self.assert_log_matches("worker-logs", r"INFO.*Worker%20task")
