"""Tests for the viceroy testing framework functionality."""

import pytest
import requests

from fastly_compute.testing import ViceroyTestBase, create_viceroy_server_fixture


@pytest.mark.integration
class TestViceroyTestingFramework(ViceroyTestBase):
    """Tests that verify the testing framework itself works correctly."""

    def test_viceroy_server_fixture_provides_server_info(self, viceroy_server):
        """Test that the viceroy_server fixture provides expected attributes."""
        # Check that the fixture returns a ViceroyServer with expected attributes
        assert hasattr(viceroy_server, "process")
        assert hasattr(viceroy_server, "base_url")
        assert hasattr(viceroy_server, "output_lines")

        # Check that base_url is properly formatted
        assert viceroy_server.base_url.startswith("http://127.0.0.1:")

        # Check that output_lines contains viceroy startup output
        assert len(viceroy_server.output_lines) > 0
        listening_lines = [
            line for line in viceroy_server.output_lines if "Listening on" in line
        ]
        assert len(listening_lines) > 0

    def test_get_method_works(self, viceroy_server):
        """Test that the get() helper method works correctly."""
        response = self.get("/info", viceroy_server)

        # Verify it returns a requests.Response object
        assert isinstance(response, requests.Response)
        assert response.status_code == 200

    def test_post_method_works(self, viceroy_server):
        """Test that the post() helper method works correctly."""
        response = self.post("/nonexistent", viceroy_server, json={"test": "data"})

        # Verify it returns a requests.Response object
        assert isinstance(response, requests.Response)
        # POST to nonexistent endpoint should return 404
        assert response.status_code == 404

    def test_request_method_works(self, viceroy_server):
        """Test that the request() helper method works correctly."""
        response = self.request("GET", "/info", viceroy_server)

        # Verify it returns a requests.Response object
        assert isinstance(response, requests.Response)
        assert response.status_code == 200

    def test_request_timeout_handling(self, viceroy_server):
        """Test that request timeouts work correctly."""
        # Test that normal requests work with reasonable timeout
        response = self.get("/info", viceroy_server, timeout=5.0)
        assert response.status_code == 200

        # Test that very short timeouts raise TimeoutError
        with pytest.raises(requests.exceptions.ReadTimeout):
            self.get("/info", viceroy_server, timeout=0.001)

    def test_custom_request_timeout_setting(self, viceroy_server):
        """Test that custom REQUEST_TIMEOUT class attribute works."""
        # Temporarily change the timeout
        original_timeout = self.REQUEST_TIMEOUT
        self.REQUEST_TIMEOUT = 1

        try:
            # This should work with 1 second timeout
            response = self.get("/info", viceroy_server)
            assert response.status_code == 200
        finally:
            # Restore original timeout
            self.REQUEST_TIMEOUT = original_timeout


class TestCustomWasmFile(ViceroyTestBase):
    """Test custom WASM file configuration."""

    # Use the same WASM file but test the configuration mechanism
    WASM_FILE = "app.wasm"

    def test_custom_wasm_file_attribute(self, viceroy_server):
        """Test that custom WASM_FILE attribute is respected."""
        # This test verifies that the WASM_FILE attribute mechanism works
        # The server should start successfully with our custom WASM file
        response = self.get("/info", viceroy_server)
        assert response.status_code == 200


# Test the factory function
custom_server = create_viceroy_server_fixture("app.wasm")


class TestFactoryFunction:
    """Test the create_viceroy_server_fixture factory function."""

    def test_factory_function_creates_working_fixture(self, custom_server):
        """Test that the factory function creates a working viceroy server."""
        # Check that the fixture returns a ViceroyServer with expected attributes
        assert hasattr(custom_server, "process")
        assert hasattr(custom_server, "base_url")
        assert hasattr(custom_server, "output_lines")

        # Test that we can make requests to it
        response = requests.get(f"{custom_server.base_url}/info")
        assert response.status_code == 200
