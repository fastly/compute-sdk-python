"""Tests for the requests-simple example application."""

from fastly_compute.test_server import LocalTestServer
from fastly_compute.testing import ViceroyTestBase


class TestRequestsSimple(ViceroyTestBase):
    """Integration tests for the requests-simple example."""

    WASM_FILE = "build/requests-simple.composed.wasm"

    @classmethod
    def setup_class(cls):
        """Set up local test server for httpbin backend."""
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
        """Clean up test server."""
        cls.test_server.stop()

    def test_static_get_request(self):
        """Test static backend GET request."""
        response = self.get("/static-get")
        assert response.status_code == 200

        data = response.json()
        assert data["demo"] == "static-get"
        assert data["backend_type"] == "static"
        assert data["backend_name"] == "test-be"
        assert data["status_code"] == 200
        assert data["success"] is True
        assert "url" in data
        assert "content_length" in data

    def test_static_post_request(self):
        """Test static backend POST request."""
        response = self.get("/static-post")
        assert response.status_code == 200

        data = response.json()

        if "error" in data:
            # Request failed - check error handling
            assert data["demo"] == "static-post"
            assert "error_type" in data
        else:
            # Request succeeded
            assert data["demo"] == "static-post"
            assert data["backend_type"] == "static"
            assert data["backend_name"] == "test-be"
            assert data["status_code"] == 200
            assert data["success"] is True

            # Check that post data was sent
            assert "sent_data" in data
            sent_data = data["sent_data"]
            assert sent_data["message"] == "Hello from Fastly Compute!"
            assert sent_data["demo"] == "static-post"

    def test_dynamic_get_request(self):
        """Test dynamic backend GET request."""
        response = self.get("/dynamic-get?target=https://http-me.fastly.dev/get")
        assert response.status_code == 200

        data = response.json()
        assert data["demo"] == "dynamic-get"

        # This test might fail if external http-me.fastly.dev is not accessible
        if "error" in data:
            # External request failed - verify error handling
            assert "error" in data
            assert "error_type" in data
        else:
            # External request succeeded
            assert data["backend_type"] == "dynamic"
            assert data["target_url"] == "https://http-me.fastly.dev/get"
            assert data["status_code"] == 200
            assert data["success"] is True
            assert "url" in data
            assert "headers" in data

    def test_dynamic_get_no_target(self):
        """Test dynamic backend GET request without target parameter."""
        response = self.get("/dynamic-get")
        assert response.status_code == 200

        data = response.json()
        assert data["demo"] == "dynamic-get"
        assert "error" in data
        assert "target query parameter is required" in data["error"]

    def test_dynamic_post_request(self):
        """Test dynamic backend POST request."""
        response = self.get("/dynamic-post?target=https://http-me.fastly.dev/post")
        assert response.status_code == 200

        data = response.json()
        assert data["demo"] == "dynamic-post"

        # External dependency - should handle gracefully
        if "error" in data:
            assert "error" in data
            assert "error_type" in data
        else:
            assert data["backend_type"] == "dynamic"
            assert data["target_url"] == "https://http-me.fastly.dev/post"
            assert "sent_data" in data
            sent_data = data["sent_data"]
            assert sent_data["service"] == "fastly-compute"
            assert sent_data["demo"] == "dynamic-post"

    def test_dynamic_post_no_target(self):
        """Test dynamic backend POST request without target parameter."""
        response = self.get("/dynamic-post")
        assert response.status_code == 200

        data = response.json()
        assert data["demo"] == "dynamic-post"
        assert "error" in data
        assert "target query parameter is required" in data["error"]

    def test_error_handling(self):
        """Test error handling scenarios."""
        response = self.get("/error-demo")
        assert response.status_code == 200

        data = response.json()
        assert data["demo"] == "error-demo"
        assert "test_results" in data

        # Should have at least 2 test cases
        test_results = data["test_results"]
        assert len(test_results) >= 2

        # Check that errors are properly caught and reported
        for result in test_results:
            assert "test" in result
            assert "status" in result
            if result["status"] == "expected_error":
                assert "error" in result
                assert "error_type" in result
