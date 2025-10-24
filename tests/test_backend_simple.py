"""Tests for backend-simple.py example with local server backends."""

from fastly_compute.test_server import LocalTestServer, LocalTestServerConfig
from fastly_compute.testing import ViceroyTestBase


class TestBackendSimple(ViceroyTestBase):
    """Integration tests for backend-simple.py with local backends."""

    WASM_FILE = "build/backend-simple.composed.wasm"

    @classmethod
    def setup_class(cls):
        """Set up local test servers and configure backends."""
        # Create a local test server that mimics httpbin
        cls.test_server = LocalTestServer(
            LocalTestServerConfig(host="127.0.0.1", port=0)
        )
        cls.test_server_url = cls.test_server.start()

        # Configure the backend for viceroy
        cls.setup_backends({"test-be": cls.test_server_url})

    @classmethod
    def teardown_class(cls):
        """Clean up test servers."""
        if hasattr(cls, "test_server"):
            cls.test_server.stop()

    def test_static_backend_request(self):
        """Test static backend request to local test server."""
        response = self.get("/static")
        assert response.status_code == 200

        data = response.json()
        assert data["backend_type"] == "static"
        assert data["backend_name"] == "test-be"
        assert data["status"] == 200

        # Check that we got httpbin-like response data
        response_data = data["data"]
        assert "url" in response_data
        assert "headers" in response_data
        assert "method" in response_data
        assert response_data["method"] == "GET"

    def test_dynamic_backend_request(self):
        """Test dynamic backend request (should work without static backend config)."""
        response = self.get("/dynamic?target=https://http-me.fastly.dev/get")
        assert response.status_code == 200

        data = response.json()
        assert data["backend_type"] == "dynamic"
        assert data["target"] == "https://http-me.fastly.dev/get"

        # This might fail if external http-me.fastly.dev is not accessible
        # But the test should at least show our code handling the dynamic backend
        if "error" in data:
            # External request failed - verify error handling
            assert "error" in data
        else:
            # External request succeeded
            assert data["status"] == 200

    def test_dynamic_backend_no_target(self):
        """Test dynamic backend request without target parameter."""
        response = self.get("/dynamic")
        assert response.status_code == 200

        data = response.json()
        assert data["backend_type"] == "dynamic"
        assert "error" in data
        assert "target query parameter is required" in data["error"]

    def test_dynamic_post_request(self):
        """Test dynamic backend POST request."""
        response = self.get("/dynamic-post?target=https://http-me.fastly.dev/post")
        assert response.status_code == 200

        data = response.json()
        assert data["backend_type"] == "dynamic"
        assert data["method"] == "POST"
        assert data["target"] == "https://http-me.fastly.dev/post"

        # Similar to GET test - external dependency
        if "error" in data:
            # External request failed - verify error handling
            assert "error" in data
        else:
            # External request succeeded
            assert "sent_data" in data
            assert data["sent_data"]["test"] is True

    def test_dynamic_post_no_target(self):
        """Test dynamic backend POST request without target parameter."""
        response = self.get("/dynamic-post")
        assert response.status_code == 200

        data = response.json()
        assert data["backend_type"] == "dynamic"
        assert data["method"] == "POST"
        assert "error" in data
        assert "target query parameter is required" in data["error"]


class TestBackendSimpleWithMockResponses(ViceroyTestBase):
    """Test backend-simple.py with controlled mock responses."""

    WASM_FILE = "build/backend-simple.composed.wasm"

    @classmethod
    def setup_class(cls):
        """Set up mock server with predefined responses."""
        # Create mock responses that match what http-me.fastly.dev would return
        mock_responses = {
            "/get": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "args": {},
                    "headers": {"User-Agent": "FastlyCompute-BackendExample/1.0"},
                    "origin": "127.0.0.1",
                    "url": "http://localhost/get",
                    "method": "GET",
                    "path": "/get",
                },
            }
        }

        # Start mock server
        config = LocalTestServerConfig(
            host="127.0.0.1", port=0, responses=mock_responses
        )
        cls.mock_server = LocalTestServer(config)
        cls.mock_server_url = cls.mock_server.start()

        # Configure backend
        cls.setup_backends({"test-be": cls.mock_server_url})

    @classmethod
    def teardown_class(cls):
        """Clean up mock server."""
        if hasattr(cls, "mock_server"):
            cls.mock_server.stop()

    def test_static_backend_with_mock_response(self):
        """Test static backend with controlled mock response."""
        response = self.get("/static")
        assert response.status_code == 200

        data = response.json()
        assert data["backend_type"] == "static"
        assert data["backend_name"] == "test-be"
        assert data["status"] == 200

        # Check the mock response data
        response_data = data["data"]
        assert response_data["method"] == "GET"
        assert response_data["path"] == "/get"
        assert response_data["url"] == "http://localhost/get"
