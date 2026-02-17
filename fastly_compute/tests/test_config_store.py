"""Integration tests for Config Store functionality."""

from pytest import raises

from fastly_compute.config_store import ConfigStore
from fastly_compute.exceptions.types.open_error import NotFound
from fastly_compute.testing import AutoViceroyTestBase, on_viceroy


class TestConfigStore(AutoViceroyTestBase):
    """Config store integration tests."""

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

    def assert_get_value(
        self, store: str, key: str, expected: str | None, default: str | None = None
    ) -> None:
        """Assert that getting a key returns the expected value."""
        value = self.config_get(store, key, default=default)
        assert value == expected

    @on_viceroy
    def config_get(cls, store_name, key, default=None):
        """Return the value associated with a config store key."""
        with ConfigStore.open(store_name) as config:
            return config.get(key, default)

    @on_viceroy
    def config_contains(cls, store_name, key):
        """Return whether a given key exists in a config store."""
        with ConfigStore.open(store_name) as config:
            return key in config

    def test_open_nonexistent_store(self):
        """Test opening a non-existent config store raises error."""
        with raises(NotFound):
            self.config_get("nonexistent", "key")

    def test_get_string_value(self):
        """Test getting a string value."""
        self.assert_get_value("test-config", "string_key", "hello world")

    def test_get_nonexistent_key(self):
        """Test getting a nonexistent key returns None."""
        self.assert_get_value("test-config", "nonexistent", None)

    def test_get_with_default(self):
        """Test getting with a default value."""
        self.assert_get_value("test-config", "nonexistent", "my_default", "my_default")

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
        assert self.config_contains("test-config", "string_key")

    def test_contains_nonexistent_key(self):
        """Test that contains returns False for non-existent keys."""
        assert not self.config_contains("test-config", "nonexistent")

    def test_contains_empty_string_value(self):
        """Test that contains returns True for keys with empty string values."""
        assert self.config_contains("test-config", "empty_string")
