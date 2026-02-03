"""Integration tests for Config Store functionality."""

from fastly_compute.testing import ViceroyTestBase


class TestConfigStore(ViceroyTestBase):
    """Config store integration tests."""

    WASM_FILE = "build/config-store.composed.wasm"

    VICEROY_CONFIG = {
        "local_server": {
            "config_stores": {
                "test-config": {
                    "format": "inline-toml",
                    "contents": {
                        "string_key": "hello world",
                        "empty_string": "",
                        "whitespace": "   ",
                        "special_chars": "!@#$%^&*()",
                        "unicode": "Hello 世界 🌍",
                        "large_value": "x" * 8000,  # 8000 byte value for buffer tests
                    },
                }
            }
        }
    }

    def assert_get_value(self, store: str, key: str, expected: str | None) -> None:
        """Assert that getting a key returns the expected value."""
        response = self.get(f"/get/{store}/{key}")
        assert response.status_code == 200
        assert response.json() == {"value": expected}

    def assert_get_value_with_default(
        self, store: str, key: str, default: str, expected: str
    ) -> None:
        """Assert that getting a key with a default returns the expected value."""
        response = self.get(f"/get/{store}/{key}/{default}")
        assert response.status_code == 200
        assert response.json() == {"value": expected}

    def assert_get_error(self, store: str, key: str, error_type: str) -> None:
        """Assert that getting a key raises an error."""
        response = self.get(f"/get/{store}/{key}")
        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == error_type

    def test_open_nonexistent_store(self):
        """Test opening a non-existent config store raises error."""
        response = self.get("/get/nonexistent/key")
        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "NotFound"

    def test_get_string_value(self):
        """Test getting a string value."""
        self.assert_get_value("test-config", "string_key", "hello world")

    def test_get_nonexistent_key(self):
        """Test getting a nonexistent key returns None."""
        self.assert_get_value("test-config", "nonexistent", None)

    def test_get_with_default(self):
        """Test getting with a default value."""
        self.assert_get_value_with_default(
            "test-config", "nonexistent", "my_default", "my_default"
        )

    def test_empty_string_value(self):
        """Test handling of empty string values."""
        self.assert_get_value("test-config", "empty_string", "")

    def test_whitespace_value(self):
        """Test handling of whitespace values."""
        self.assert_get_value("test-config", "whitespace", "   ")

    def test_special_characters(self):
        """Test handling of special characters."""
        self.assert_get_value("test-config", "special_chars", "!@#$%^&*()")

    def test_unicode_support(self):
        """Test handling of unicode characters."""
        self.assert_get_value("test-config", "unicode", "Hello 世界 🌍")

    def test_large_values(self):
        """Test that large values are handled correctly."""
        self.assert_get_value("test-config", "large_value", "x" * 8000)

    def test_contains_existing_key(self):
        """Test that contains returns True for existing keys."""
        response = self.get("/contains/test-config/string_key")
        assert response.status_code == 200
        assert response.json() == {"contains": True}

    def test_contains_nonexistent_key(self):
        """Test that contains returns False for non-existent keys."""
        response = self.get("/contains/test-config/nonexistent")
        assert response.status_code == 200
        assert response.json() == {"contains": False}

    def test_contains_empty_string_value(self):
        """Test that contains returns True for keys with empty string values."""
        response = self.get("/contains/test-config/empty_string")
        assert response.status_code == 200
        assert response.json() == {"contains": True}
