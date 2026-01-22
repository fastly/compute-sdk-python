"""Config Store API for Fastly Compute.

This module provides access to Fastly Config Stores, which allow you to store
configuration data that can be updated without redeploying your service.

Example::

    from fastly_compute.config_store import ConfigStore

    with ConfigStore.open("my-config") as config:
        api_url = config.get("api_url", "https://api.example.com")
"""

from wit_world.imports import config_store as wit_config_store
from wit_world.imports.types import Error_BufferLen, Error_InvalidArgument, OpenError

from fastly_compute.exceptions import FastlyError, remap_wit_errors


class ConfigStoreError(FastlyError):
    """Base exception for all config store errors."""


class ConfigStoreNotFoundError(ConfigStoreError):
    """The requested config store does not exist."""


class ConfigStoreInvalidNameError(ConfigStoreError):
    """The config store name is invalid."""


class ConfigStoreBufferTooSmallError(ConfigStoreError):
    """The buffer provided was too small for the config value.

    The required buffer size is available in the `required_size` attribute.
    """

    def __init__(self, error: Error_BufferLen):
        """Initialize with the WIT error containing the required size.

        :param error: The WIT Error_BufferLen dataclass with the required size
        """
        self.required_size = error.value
        super().__init__(
            f"Buffer too small for config store value. Required size: {self.required_size} bytes"
        )


class ConfigStoreInvalidKeyError(ConfigStoreError):
    """The key provided is invalid."""


class ConfigStore:
    """Interface to Fastly Config Store.

    Config Stores provide read-only access to configuration data that can be
    updated without redeploying your service.

    Example::

        with ConfigStore.open("app-config") as config:
            api_url = config.get("api_url", "https://api.example.com")
    """

    def __init__(self, store: wit_config_store.Store):
        """Private constructor. Use ConfigStore.open() instead."""
        self._store = store

    @classmethod
    @remap_wit_errors(
        {
            OpenError.NOT_FOUND: ConfigStoreNotFoundError,
            OpenError.INVALID_SYNTAX: ConfigStoreInvalidNameError,
            OpenError.NAME_TOO_LONG: ConfigStoreInvalidNameError,
            OpenError.RESERVED: ConfigStoreInvalidNameError,
        }
    )
    def open(cls, name: str) -> "ConfigStore":
        """Open a config store by name.

        :param name: The name of the config store
        :return: ConfigStore instance
        :raises ConfigStoreNotFoundError: If the config store doesn't exist
        :raises ConfigStoreInvalidNameError: If the name is invalid or too long

        Example::

            config = ConfigStore.open("my-config")
        """
        store = wit_config_store.Store.open(name)
        return cls(store)

    def get(
        self, key: str, default: str | None = None, initial_buf_len: int = 1024
    ) -> str | None:
        """Get a configuration value with automatic buffer resizing.

        This method automatically handles buffer sizing for config store values.
        If the initial buffer is too small, it will automatically retry once with
        the exact size required by the host.

        :param key: The configuration key
        :param default: Default value if key not found
        :param initial_buf_len: Initial buffer size hint in bytes (default: 1024).
            This can be tuned for performance if you know your values are typically
            larger or smaller than 1KB.
        :return: Configuration value or default if not found
        :raises ConfigStoreInvalidKeyError: If the key is invalid
        :raises ConfigStoreBufferTooSmallError: If the value is too large even after
            automatic resizing (should not happen unless there's a host-level bug)

        Example::

            config = ConfigStore.open("app-config")
            # Basic usage with default buffer size
            api_url = config.get("api_url", "https://api.example.com")

            # Optimize for large values by using a larger initial buffer
            large_value = config.get("large_config", initial_buf_len=16384)
        """
        # Try with the initial buffer size
        try:
            result = self._get_raw(key, initial_buf_len)
        except ConfigStoreBufferTooSmallError as e:
            # Buffer was too small. The exception contains the exact required size.
            # Retry ONCE with the exact size needed. If this second attempt fails,
            # let the exception propagate (no infinite recursion).
            result = self._get_raw(key, e.required_size)

        if result is None:
            result = default

        return result

    @remap_wit_errors(
        {
            Error_BufferLen: ConfigStoreBufferTooSmallError,
            Error_InvalidArgument: ConfigStoreInvalidKeyError,
        }
    )
    def _get_raw(self, key: str, max_len: int) -> str | None:
        """Internal method to get a value with a specific buffer size.

        :param key: The configuration key
        :param max_len: Maximum buffer length
        :return: Configuration value or None if not found
        :raises ConfigStoreBufferTooSmallError: If the buffer is too small
        :raises ConfigStoreInvalidKeyError: If the key is invalid
        """
        return self._store.get(key, max_len)

    def contains(self, key: str) -> bool:
        """Check if a key exists in the config store.

        Uses a zero-length buffer to efficiently check for key existence without
        retrieving the value.

        :param key: The configuration key
        :return: True if the key exists, False otherwise
        :raises ConfigStoreInvalidKeyError: If the key is invalid

        Example::

            config = ConfigStore.open("app-config")
            if config.contains("feature_flag"):
                print("Feature flag exists")
        """
        try:
            # Use a 0-length buffer to check existence without retrieving the value
            result = self._get_raw(key, 0)
            return result is not None
        except ConfigStoreBufferTooSmallError:
            # Buffer too small means the key exists with a non-empty value
            return True
        except ConfigStoreInvalidKeyError:
            # Re-raise invalid key errors
            raise

    def close(self) -> None:
        """Explicitly close the config store, releasing its resources.

        This is called automatically when using the config store as a context
        manager. If not called explicitly, resources will eventually be freed
        by the garbage collector.

        Note: Attempting to use the config store after it is closed will result
        in a trap.
        """
        self._store.__exit__(None, None, None)

    def __enter__(self) -> "ConfigStore":
        """Context manager entry.

        Allows use of ConfigStore in a 'with' statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._store.__exit__(exc_type, exc_val, exc_tb)
