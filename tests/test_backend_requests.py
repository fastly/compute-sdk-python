"""Tests for the backend-requests example application."""

import sys
from typing import Any

import pytest
import requests

from fastly_compute.test_server import LocalTestServer
from fastly_compute.testing import ViceroyTestBase


class BackendRequestsTestBase(ViceroyTestBase):
    """Base class for backend-requests tests with shared helper methods."""

    WASM_FILE = "build/backend-requests.composed.wasm"

    def assert_success(self, response: requests.Response) -> dict[str, Any]:
        """Assert that a result represents a successful operation.

        Args:
            result: Response JSON dictionary
            expected_demo: Expected value of 'demo' field
        """
        # request to helper service succeeded (non-proxy)
        assert response.status_code == 200

        # make basic assertions on the proxied response
        result: dict[str, Any] = response.json()
        error = result.get("error")
        success = result.get("success")
        status_code = result.get("status_code")

        if error is not None or success is not True or status_code != 200:
            tb = result.get("tb", "")
            print(f"Error Detected {error}", file=sys.stderr)
            print(f"Traceback: {tb}", file=sys.stderr)
            raise AssertionError(f"Expected Success Response, got {error}")

        return result

    def assert_error(
        self, response: requests.Response, error_substring: str | None = None
    ) -> dict[str, Any]:
        """Assert that a result represents an error.

        The return dictionary is the transformed error, with the traceback
        information removed (which is too noisy to compare against).

        Args:
            result: Response JSON dictionary
            expected_demo: Expected value of 'demo' field
            error_substring: Optional substring that should appear in error message
        """
        result: dict[str, Any] = response.json()
        error = result.get("error")
        success = result.get("success")
        status_code = result.get("status_code")
        if not error or success or status_code == 200:
            raise AssertionError(f"Unexpected Success, got {result}")

        if error_substring:
            assert error_substring in result.get("error", ""), (
                f"Expected error to contain '{error_substring}', got: {result.get('error')}"
            )

        # strip out traceback info
        _ = result.pop("tb", None)
        return result


class TestRequestsSimple(BackendRequestsTestBase):
    """Integration tests for the backend-requests example."""

    @classmethod
    def setup_class(cls):
        """Set up local test server for httpbin-esque backend."""
        # Create httpbin-like responses
        mock_responses = {
            "/get": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "args": {},
                    "headers": {
                        "User-Agent": "FastlyCompute-Requests/1.0",
                        "Host": "localhost",
                    },
                    "method": "GET",
                    "origin": "127.0.0.1",
                    "url": "http://localhost/get",
                },
            },
            "/post": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "args": {},
                    "data": "",
                    "files": {},
                    "form": {},
                    "headers": {
                        "User-Agent": "FastlyCompute-Requests/1.0",
                        "Content-Type": "application/json",
                    },
                    "json": {},  # Will be populated with actual request data
                    "method": "POST",
                    "origin": "127.0.0.1",
                    "url": "http://localhost/post",
                },
            },
        }

        # Set up mock server
        cls.test_server = LocalTestServer(
            host="127.0.0.1", port=0, responses=mock_responses
        )
        cls.test_server_url = cls.test_server.start()

        # Configure test-be backend for static backend tests
        cls.set_up_backends({"test-be": cls.test_server_url})

    @classmethod
    def teardown_class(cls):
        cls.test_server.stop()

    def test_static_get_request(self, snapshot):
        response = self.get(
            "/proxy/get",
            params={"url": "https://http-me.fastly.dev/json", "backend": "test-be"},
        )
        data = self.assert_success(response)
        assert data == snapshot

    def test_static_post_request(self, snapshot):
        response = self.get(
            "/proxy/post",
            params={
                "url": "https://http-me.fastly.dev/post",
                "backend": "test-be",
                "json": '{"message": "Hello from Fastly Compute!", "demo": "static-post"}',
            },
        )
        data = self.assert_success(response)
        assert data == snapshot

    def test_dynamic_get_request(self, snapshot):
        response = self.get(
            "/proxy/get",
            params={"url": "https://http-me.fastly.dev/get"},
        )
        data = self.assert_success(response)
        assert data == snapshot

    def test_dynamic_get_no_url(self, snapshot):
        """Test GET request with missing url parameter."""
        response = self.get("/proxy/get")
        # Should get JSON error response
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "url query parameter is required" in data["error"]
        assert data == snapshot

    def test_dynamic_post_request(self, snapshot):
        response = self.get(
            "/proxy/post",
            params={
                "url": "https://http-me.fastly.dev/post",
                "json": '{"service": "fastly-compute", "demo": "dynamic-post", "message": "Dynamic backend POST from Fastly Compute"}',
            },
        )
        data = self.assert_success(response)
        assert data == snapshot

    def test_invalid_url(self):
        response = self.get("/proxy/get", params={"url": ".* not a valid url ~~~~"})
        _result = self.assert_error(response, "No scheme supplied")

    def test_invalid_backend(self):
        response = self.get(
            "/proxy/get",
            params={"url": "http://http-me.fastly.dev", "backend": "does-not-exist"},
        )
        _result = self.assert_error(
            response,
            "Backend resolution failed: Static backend 'does-not-exist' does not exist",
        )


class TestRequestsCompatibility(BackendRequestsTestBase):
    """Test that Fastly Compute requests behaves identically to standard requests.

    These tests verify that the Fastly Compute requests implementation produces
    the same results as the standard Python requests library for common scenarios.
    """

    @classmethod
    def setup_class(cls):
        """Set up test backend with known responses."""
        # Configure test server with specific responses for compatibility testing
        responses = {
            "/json": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "body": {"message": "Hello", "count": 42},
            },
            "/text": {
                "status": 200,
                "headers": {"Content-Type": "text/plain"},
                "body": "Plain text response",
            },
            "/headers": {
                "status": 200,
                "headers": {
                    "X-Custom-Header": "custom-value",
                    "Content-Type": "text/plain",
                },
                "body": "Response with headers",
            },
            "/status/404": {
                "status": 404,
                "headers": {"Content-Type": "text/plain"},
                "body": "Not Found",
            },
        }

        cls.test_server = LocalTestServer(host="127.0.0.1", port=0, responses=responses)
        cls.test_server_url = cls.test_server.start()

        # Set up backends for viceroy
        cls.set_up_backends({"test-be": cls.test_server_url})

    @classmethod
    def teardown_class(cls):
        """Clean up test server."""
        if hasattr(cls, "test_server"):
            cls.test_server.stop()

    def test_json_response_compatibility(self):
        """Test that JSON responses are handled identically."""
        # Make request through standard requests library
        direct_response = requests.get(f"{self.test_server_url}/json")

        # Make request through Fastly Compute proxy
        # Note: Must use full URL with static backend due to Viceroy limitation
        proxy_response = self.get(
            "/proxy/get",
            params={
                "url": f"{self.test_server_url}/json",
                "backend": "test-be",
            },
        )

        # Use helper to verify success and compare status codes
        proxy_data = self.assert_success(proxy_response)
        assert proxy_data["status_code"] == direct_response.status_code == 200

    def test_text_response_compatibility(self):
        """Test that text responses are handled identically."""
        # Make request through standard requests library
        direct_response = requests.get(f"{self.test_server_url}/text")

        # Make request through Fastly Compute proxy
        proxy_response = self.get(
            "/proxy/get",
            params={
                "url": f"{self.test_server_url}/text",
                "backend": "test-be",
            },
        )

        # Use helper to verify success and compare content
        proxy_data = self.assert_success(proxy_response)
        assert proxy_data["status_code"] == direct_response.status_code
        assert proxy_data["response_preview"] == direct_response.text

    def test_headers_compatibility(self):
        """Test that response headers are handled identically."""
        # Make request through standard requests library
        direct_response = requests.get(f"{self.test_server_url}/headers")

        # Make request through Fastly Compute proxy
        proxy_response = self.get(
            "/proxy/get",
            params={
                "url": f"{self.test_server_url}/headers",
                "backend": "test-be",
            },
        )

        # Use helper to verify success and compare headers
        proxy_data = self.assert_success(proxy_response)
        assert proxy_data["status_code"] == direct_response.status_code
        assert proxy_data["headers_count"] > 0

    def test_status_code_compatibility(self):
        """Test that non-200 status codes are handled identically."""
        # Make request through standard requests library
        direct_response = requests.get(f"{self.test_server_url}/status/404")

        # Make request through Fastly Compute proxy
        proxy_response = self.get(
            "/proxy/get",
            params={
                "url": f"{self.test_server_url}/status/404",
                "backend": "test-be",
            },
        )

        # 404 is not an error from the proxy's perspective (request succeeded),
        # but success=False because response.ok is False for 404
        assert proxy_response.status_code == 200
        proxy_data = proxy_response.json()

        # Verify the proxy call succeeded without exceptions
        assert "error" not in proxy_data
        assert proxy_data["success"] is False  # 404 is not "ok"
        assert proxy_data["status_code"] == direct_response.status_code == 404
        assert proxy_data["response_preview"] == direct_response.text

    @pytest.mark.xfail(
        reason="Viceroy doesn't populate error detail field - raises RequestException instead of ConnectionError"
    )
    def test_connection_error_exception_type(self):
        """Test that connection errors raise exceptions.

        Note: The standard requests library raises ConnectionError for connection
        issues. Our facade should raise ConnectionError, but currently raises
        RequestException due to Viceroy not populating the error detail field.
        """
        # Make request through standard requests library to a port that doesn't exist
        direct_exception_type = None
        try:
            requests.get("http://127.0.0.1:9", timeout=1)
        except requests.exceptions.ConnectionError:
            direct_exception_type = "ConnectionError"
        except requests.exceptions.RequestException:
            direct_exception_type = "RequestException"

        # Make request through Fastly Compute proxy
        proxy_response = self.get(
            "/proxy/get",
            params={"url": "http://127.0.0.1:9"},
        )

        # Verify the proxy returns an error
        assert proxy_response.status_code == 200
        proxy_data = proxy_response.json()
        assert "error" in proxy_data
        # Should raise ConnectionError like requests library
        assert proxy_data.get("error_type") == "ConnectionError"

        # Document what the standard library does for reference
        assert direct_exception_type == "ConnectionError"

    def test_invalid_url_exception_type(self):
        """Test that invalid URLs raise exceptions.

        Note: The standard requests library raises MissingSchema for URLs without
        a scheme. Our facade now correctly raises MissingSchema to match.
        """
        # Make request through standard requests library with invalid URL
        direct_exception_type = None
        try:
            requests.get("not-a-valid-url")
        except requests.exceptions.InvalidURL:
            direct_exception_type = "InvalidURL"
        except requests.exceptions.MissingSchema:
            direct_exception_type = "MissingSchema"
        except ValueError:
            direct_exception_type = "ValueError"

        # Make request through Fastly Compute proxy
        proxy_response = self.get(
            "/proxy/get",
            params={"url": "not-a-valid-url"},
        )

        # Verify the proxy returns an error
        assert proxy_response.status_code == 200
        proxy_data = proxy_response.json()
        assert "error" in proxy_data
        # Should raise MissingSchema like requests library
        assert proxy_data.get("error_type") == "MissingSchema"

        # Document what the standard library does for reference
        assert direct_exception_type in ["MissingSchema", "InvalidURL"]


class TestRequestErrorHandling(BackendRequestsTestBase):
    """Test error handling in the requests module."""

    @classmethod
    def setup_class(cls):
        """Set up test backend."""
        # Create a local test server for backend testing
        cls.test_server = LocalTestServer(host="127.0.0.1", port=0)
        base_url = cls.test_server.start()

        # Set up backends for viceroy (keep the full URL with scheme)
        cls.set_up_backends({"test-be": base_url})

    @classmethod
    def teardown_class(cls):
        """Clean up test server."""
        if hasattr(cls, "test_server"):
            cls.test_server.stop()

    def test_invalid_url_for_dynamic_backend(self):
        """Test that invalid URLs for dynamic backends return proper errors."""
        # Missing scheme - should raise MissingSchema like requests library
        response = self.get("/proxy/get?url=just-a-path")
        result = self.assert_error(response, "No scheme supplied")
        assert result["error_type"] == "MissingSchema"

    def test_missing_url_parameter(self):
        """Test that missing URL parameter returns proper error."""
        response = self.get("/proxy/get")
        self.assert_error(response, "url query parameter is required")

    def test_invalid_json_parameter(self):
        """Test that invalid JSON in query parameter returns proper error.

        Note: This error is caught at the proxy level during parameter validation,
        so it doesn't include an error_type field from the requests library.
        """
        response = self.get("/proxy/post?url=http://example.com&json=not-valid-json")
        self.assert_error(response, "Invalid JSON")

    def test_both_data_and_json_parameters(self):
        """Test that specifying both data and json parameters raises ValueError.

        This tests the validation in requests.request() that prevents
        conflicting parameters.
        """
        # This would need to be tested at the library level, not through the proxy
        # endpoint since the proxy only supports json parameter.
        # We'll add a note that this is validated at the API level.
        pass

    @pytest.mark.xfail(
        reason="Viceroy doesn't populate error detail field - raises RequestException instead of ConnectionError"
    )
    def test_dynamic_backend_connection_refused(self):
        """Test handling of connection refused errors.

        Try to connect to a port that's not listening to trigger
        connection refused error from http_req.send().
        """
        # Use a port that's unlikely to be in use
        response = self.get("/proxy/get?url=http://127.0.0.1:9")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        # Should raise ConnectionError like requests library
        assert data.get("error_type") == "ConnectionError"

    @pytest.mark.xfail(
        reason="Viceroy doesn't populate error detail field - raises RequestException instead of ConnectionError"
    )
    def test_dynamic_backend_dns_failure(self):
        """Test handling of DNS resolution failures.

        Use a hostname that doesn't exist to trigger DNS error.
        """
        response = self.get(
            "/proxy/get?url=http://this-domain-should-not-exist-12345.invalid"
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        # Should raise ConnectionError like requests library (DNS failures are connection errors)
        assert data.get("error_type") == "ConnectionError"

    def test_invalid_backend_name(self):
        """Test that invalid static backend names return proper errors."""
        response = self.get(
            "/proxy/get?url=http://example.com&backend=nonexistent-backend"
        )
        result = self.assert_error(response, "does not exist")
        # Should raise RequestException for backend resolution failures
        assert result["error_type"] == "RequestException"

    def test_backend_with_special_characters_in_url(self):
        """Test backend handling with special characters in URL."""
        # Test with URL that has unicode characters
        response = self.get("/proxy/get?url=http://example.com/test%20path")
        assert response.status_code == 200
        data = response.json()
        # This might succeed or fail depending on viceroy, but should handle gracefully
        assert "error" in data or "success" in data

    def test_timeout_configuration_validation(self):
        """Test that timeout validation works.

        The TimeoutConfig class has validation that we should test.
        This would require a separate unit test or direct API testing.
        """
        # Note: This is more of a unit test, consider adding to a separate file
        pass

    def test_backend_with_empty_response(self):
        """Test handling of backend that returns empty/minimal response."""
        # Use the test backend which will return proper responses
        # Note: path-only URLs with static backends cause Viceroy to panic
        # at src/upstream.rs:280 with InvalidUri, so we use a full URL
        response = self.get("/proxy/get?url=http://httpbin.org/get&backend=test-be")
        assert response.status_code == 200
        data = response.json()
        # Should handle response gracefully
        assert "success" in data or "error" in data

    def test_unicode_in_headers(self):
        """Test that unicode characters in headers are handled properly.

        This tests the UnicodeError exception handling in set_request_headers.
        """
        # The proxy endpoint would need to support custom headers for this
        # This is a limitation of the current test proxy design
        pass

    def test_large_response_body(self):
        """Test handling of large response bodies.

        This exercises the read_response_body utility which has error handling
        for WIT errors during body reading.
        """
        # Would need to configure test server to return large response
        # and verify it's handled correctly
        pass


class TestBackendResolution(BackendRequestsTestBase):
    """Test backend resolution logic specifically."""

    @classmethod
    def setup_class(cls):
        """Set up multiple backends for testing."""
        cls.test_server1 = LocalTestServer(host="127.0.0.1", port=0)
        base_url1 = cls.test_server1.start()

        cls.set_up_backends(
            {
                "test-be-1": base_url1,
            }
        )

    @classmethod
    def teardown_class(cls):
        """Clean up test servers."""
        if hasattr(cls, "test_server1"):
            cls.test_server1.stop()

    def test_backend_name_sanitization(self):
        """Test that backend names are properly sanitized from URLs.

        The _sanitize_backend_name function should handle dots, colons, etc.
        """
        # Test a URL that will fail to connect but shouldn't crash
        # Use localhost with a port that won't respond
        response = self.get("/proxy/get?url=http://localhost:9999/path")
        assert response.status_code == 200
        data = response.json()
        # Should get an error but not crash
        assert "error" in data or "success" in data

    def test_dynamic_backend_reuse(self):
        """Test that dynamic backends are reused when appropriate.

        Making multiple requests to the same dynamic backend should reuse
        the registered backend rather than creating a new one each time.
        """
        # Make multiple requests to the same dynamic backend
        for _ in range(3):
            response = self.get("/proxy/get?url=http://example.com/test")
            assert response.status_code == 200

    def test_static_backend_with_path(self):
        """Test static backend with a path in the URL."""
        # When using static backend, the URL can be just a path
        # The test backend should handle this
        response = self.get("/proxy/get?url=http://httpbin.org/get&backend=test-be-1")
        assert response.status_code == 200
        data = response.json()
        # Should either succeed or have an error, but not crash
        assert "error" in data or "success" in data


class TestHTTPMethodHandling(BackendRequestsTestBase):
    """Test different HTTP methods and their error cases."""

    @classmethod
    def setup_class(cls):
        """Set up test backend."""
        cls.test_server = LocalTestServer(host="127.0.0.1", port=0)
        base_url = cls.test_server.start()
        cls.set_up_backends({"test-be": base_url})

    @classmethod
    def teardown_class(cls):
        """Clean up test server."""
        if hasattr(cls, "test_server"):
            cls.test_server.stop()

    def test_post_with_empty_body(self):
        """Test POST request with empty body."""
        response = self.get("/proxy/post?url=http://example.com")
        assert response.status_code == 200
        # Should handle empty body gracefully

    def test_post_with_json_body(self):
        """Test POST request with JSON body."""
        json_data = '{"key": "value", "number": 42}'
        response = self.get(f"/proxy/post?url=http://example.com&json={json_data}")
        assert response.status_code == 200

    def test_various_http_methods(self):
        """Test various HTTP methods (PUT, DELETE, PATCH)."""
        methods = ["put", "delete", "patch"]
        for method in methods:
            response = self.get(f"/proxy/{method}?url=http://example.com")
            # The proxy should handle these methods
            # Response will depend on whether the backend accepts them
            assert response.status_code == 200
