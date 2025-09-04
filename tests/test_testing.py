"""Tests for the viceroy testing framework functionality."""

import pytest
import requests

from fastly_compute.testing import ViceroyTestBase


@pytest.mark.integration
class TestViceroyTestingFramework(ViceroyTestBase):
    """Tests that verify the testing framework itself works correctly."""

    def test_viceroy_server_fixture_provides_server_info(self):
        """Test that the viceroy_server fixture provides expected attributes."""
        # Check that the fixture sets up a ViceroyServer with expected attributes
        assert hasattr(self.server, "process")
        assert hasattr(self.server, "base_url")
        assert hasattr(self.server, "output_lines")

        # Check that base_url is properly formatted
        assert self.server.base_url.startswith("http://127.0.0.1:")

        # Check that output_lines contains viceroy startup output
        assert len(self.server.output_lines) > 0
        listening_lines = [
            line for line in self.server.output_lines if "Listening on" in line
        ]
        assert len(listening_lines) > 0

    def test_get_method_works(self):
        """Test that the get() helper method works correctly."""
        response = self.get("/info")

        # Verify it returns a requests.Response object
        assert isinstance(response, requests.Response)
        assert response.status_code == 200

    def test_post_method_works(self):
        """Test that the post() helper method works correctly."""
        response = self.post("/nonexistent", json={"test": "data"})

        # Verify it returns a requests.Response object
        assert isinstance(response, requests.Response)
        # POST to nonexistent endpoint should return 404
        assert response.status_code == 404

    def test_request_method_works(self):
        """Test that the request() helper method works correctly."""
        response = self.request("GET", "/info")

        # Verify it returns a requests.Response object
        assert isinstance(response, requests.Response)
        assert response.status_code == 200

    def test_request_timeout_handling(self):
        """Test that request timeouts work correctly."""
        # Test that normal requests work with reasonable timeout
        response = self.get("/info", timeout=5.0)
        assert response.status_code == 200

        # Test that very short timeouts raise TimeoutError
        with pytest.raises(requests.exceptions.ReadTimeout):
            self.get("/info", timeout=0.001)

    def test_custom_request_timeout_setting(self):
        """Test that custom REQUEST_TIMEOUT class attribute works."""
        # Temporarily change the timeout
        original_timeout = self.REQUEST_TIMEOUT
        self.REQUEST_TIMEOUT = 1

        try:
            # This should work with 1 second timeout
            response = self.get("/info")
            assert response.status_code == 200
        finally:
            # Restore original timeout
            self.REQUEST_TIMEOUT = original_timeout
