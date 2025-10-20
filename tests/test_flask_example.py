"""Tests for the Flask example application."""

from fastly_compute.testing import ViceroyTestBase


class TestFlaskApp(ViceroyTestBase):
    """Integration tests for the Flask example application."""

    WASM_FILE = "build/flask-app.composed.wasm"

    def test_hello_endpoint(self):
        """Test the hello endpoint returns expected content."""
        response = self.get("/hello/flask")

        assert response.status_code == 200
        assert response.text == "Hello flask!"

    def test_info_endpoint(self):
        """Test the info endpoint returns expected JSON with WIT data."""
        response = self.get("/info")

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")

        data = response.json()

        # Check basic service info
        assert data["service"] == "fastly-compute-python-flask"
        assert data["status"] == "ok"
        assert "message" in data

        # Check WIT API data
        assert "vcpu_time_ms" in data
        assert isinstance(data["vcpu_time_ms"], int)

    def test_error_endpoint_handling(self):
        """Test that the error endpoint returns 500."""
        response = self.get("/error")

        # The endpoint should return a 500 error due to the exception
        assert response.status_code == 500
