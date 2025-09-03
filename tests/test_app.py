"""Tests for the Fastly Compute Python service (app.wasm functionality)."""

import pytest

from fastly_compute.testing import ViceroyTestBase


@pytest.mark.integration
class TestFastlyComputeApp(ViceroyTestBase):
    """Integration tests for the Fastly Compute service functionality."""

    def test_hello_endpoint(self, viceroy_server):
        """Test the hello endpoint returns expected content."""
        response = self.get("/hello/test", viceroy_server)

        assert response.status_code == 200
        assert response.text == "Hello test!"

    def test_hello_endpoint_with_different_name(self, viceroy_server):
        """Test the hello endpoint with a different name parameter."""
        response = self.get("/hello/world", viceroy_server)

        assert response.status_code == 200
        assert response.text == "Hello world!"

    def test_info_endpoint(self, viceroy_server):
        """Test the info endpoint returns expected JSON with WIT data."""
        response = self.get("/info", viceroy_server)

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")

        data = response.json()

        # Check basic service info
        assert data["service"] == "fastly-compute-python"
        assert data["status"] == "ok"
        assert "message" in data

        # Check WIT API data
        assert "vcpu_time_ms" in data
        assert isinstance(data["vcpu_time_ms"], int)

        # Check request data
        assert data["request_method"] == "GET"
        assert data["path_info"] == "/info"

    def test_nonexistent_endpoint(self, viceroy_server):
        """Test that nonexistent endpoints return 404."""
        response = self.get("/nonexistent", viceroy_server)

        assert response.status_code == 404

    def test_post_request_handling(self, viceroy_server):
        """Test that POST requests are handled correctly."""
        # Current app.py doesn't handle POST to /api/data, so expect 404
        response = self.post("/api/data", viceroy_server, json={"key": "value"})
        assert response.status_code == 404

    def test_custom_headers(self, viceroy_server):
        """Test requests with custom headers are processed."""
        headers = {"X-Custom-Header": "test-value"}
        response = self.get("/info", viceroy_server, headers=headers)
        assert response.status_code == 200

    def test_error_endpoint_handling(self, viceroy_server):
        """Test that the error endpoint returns 500 and triggers viceroy output display."""
        response = self.get("/error", viceroy_server)

        # The endpoint should return a 500 error due to the exception
        assert response.status_code == 500

        # This test also serves to verify that the built-in hook works
        # If this test fails, we should see viceroy output in the test results
