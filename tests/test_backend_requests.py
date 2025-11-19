"""Tests for the backend-requests example application."""

from fastly_compute.test_server import LocalTestServer
from fastly_compute.testing import ViceroyTestBase


class TestRequestsSimple(ViceroyTestBase):
    """Integration tests for the backend-requests example."""

    WASM_FILE = "build/backend-requests.composed.wasm"

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

    def test_static_get_request(self, snapshot):
        """Test static backend GET request."""
        response = self.get("/static-get")
        assert response.status_code == 200
        assert response.json() == snapshot

    def test_static_post_request(self, snapshot):
        """Test static backend POST request."""
        response = self.get("/static-post")
        assert response.status_code == 200
        assert response.json() == snapshot

    def test_dynamic_get_request(self, snapshot):
        """Test dynamic backend GET request."""
        response = self.get("/dynamic-get?target=https://http-me.fastly.dev/get")
        assert response.status_code == 200
        assert response.json() == snapshot

    def test_dynamic_get_no_target(self, snapshot):
        """Test dynamic backend GET request without target parameter."""
        response = self.get("/dynamic-get")
        assert response.status_code == 200
        assert response.json() == snapshot

    def test_dynamic_post_request(self, snapshot):
        """Test dynamic backend POST request."""
        response = self.get("/dynamic-post?target=https://http-me.fastly.dev/post")
        assert response.status_code == 200
        assert response.json() == snapshot

    def test_dynamic_post_no_target(self, snapshot):
        """Test dynamic backend POST request without target parameter."""
        response = self.get("/dynamic-post")
        assert response.status_code == 200
        assert response.json() == snapshot

    def test_error_handling(self, snapshot):
        """Test error handling scenarios."""
        response = self.get("/error-demo")
        assert response.status_code == 200
        assert response.json() == snapshot
