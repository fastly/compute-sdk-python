"""Integration tests for the Fastly Compute Python service."""

import subprocess
import time
from pathlib import Path

import pytest
import requests


@pytest.mark.integration
class TestFastlyComputeService:
    """Integration tests for the Fastly Compute service running under viceroy."""

    BASE_URL = "http://127.0.0.1:7676"
    REQUEST_TIMEOUT = 10

    @pytest.fixture(scope="class", autouse=True)
    def build_service(self):
        """Build the WebAssembly component before running tests."""
        print("Building WebAssembly component...")
        result = subprocess.run(
            ["make", "app.wasm"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"Failed to build service: {result.stderr}")

    @pytest.fixture(scope="class")
    def viceroy_server(self):
        """Start viceroy server for the duration of the test class."""
        print("Starting viceroy server...")

        # Start viceroy in the background
        process = subprocess.Popen(
            ["make", "serve"],
            cwd=Path(__file__).parent.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for server to start
        # TODO: key off some other signal or logs to speed this up...
        time.sleep(10)

        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(f"Viceroy failed to start: {stderr}")

        yield process

        # Cleanup: terminate the process
        print("Stopping viceroy server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    def _get(self, path: str) -> requests.Response:
        """Make a GET request to the service."""
        return requests.get(f"{self.BASE_URL}{path}", timeout=self.REQUEST_TIMEOUT)

    def test_hello_endpoint(self, viceroy_server):
        """Test the hello endpoint returns expected content."""
        response = self._get("/hello/test")

        assert response.status_code == 200
        assert response.text == "Hello test!"

    def test_hello_endpoint_with_different_name(self, viceroy_server):
        """Test the hello endpoint with a different name parameter."""
        response = self._get("/hello/world")

        assert response.status_code == 200
        assert response.text == "Hello world!"

    def test_info_endpoint(self, viceroy_server):
        """Test the info endpoint returns expected JSON with WIT data."""
        response = self._get("/info")

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")

        data = response.json()

        # Check basic service info
        assert data["service"] == "fastly-compute-python"
        assert data["status"] == "ok"
        assert "message" in data

        # Check WIT API data
        assert "vcpu_time_ms" in data
        assert isinstance(data["vcpu_time_ms"], int | type(None))

        # Check request data
        assert data["request_method"] == "GET"
        assert data["path_info"] == "/info"

    def test_nonexistent_endpoint(self, viceroy_server):
        """Test that nonexistent endpoints return 404."""
        response = self._get("/nonexistent")

        assert response.status_code == 404

    def test_service_health(self, viceroy_server):
        """Test that the service is healthy and responsive."""
        # Make multiple requests to ensure stability
        for _ in range(3):
            response = self._get("/info")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "ok"
