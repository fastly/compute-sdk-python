"""Config Store API for Fastly Compute

This module provides access to Fastly Config Stores, which allow you to store
configuration data that can be updated without redeploying your service.

Example::

    from fastly_compute.config_store import ConfigStore

    with ConfigStore.open("my-config") as config:
        api_url = config.get("api_url", "https://api.example.com")
"""

from typing import Self

from wit_world.imports import config_store as wit_config_store

# The maximum value for a u32, used to signal that we don't want to cap
# the length of values returned by the host.  In practice, this limit
# is at 8KB, though that could change.
_MAX_U32 = 0xFFFFFFFF


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
    def open(cls, name: str) -> Self:
        """Open a config store by name.

        :param name: The name of the config store
        :return: ConfigStore instance
        :raises ~fastly_compute.exceptions.types.open_error.NotFound: If the config store doesn't exist
        :raises ~fastly_compute.exceptions.types.open_error.InvalidSyntax: If the name is invalid
        :raises ~fastly_compute.exceptions.types.open_error.NameTooLong: If the name is too long

        Example::

            config = ConfigStore.open("my-config")
        """
        store = wit_config_store.Store.open(name)
        return cls(store)

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a configuration value.

        :param key: The configuration key
        :param default: Default value if key not found
        :return: Configuration value or default if not found
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If the key is invalid

        Example::

            config = ConfigStore.open("app-config")
            api_url = config.get("api_url", "https://api.example.com")
        """
        result = self._store.get(key, _MAX_U32)
        if result is None:
            result = default

        return result

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the config store.

        :param key: The configuration key
        :return: True if the key exists, False otherwise
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If the key is invalid
        :raises KeyError: If the key is not a str

        Example::

            config = ConfigStore.open("app-config")
            if "feature_flag" in config:
                print("Feature flag exists")
        """
        if not isinstance(key, str):
            raise KeyError("Key must be a str")
        return self.get(key) is not None

    def close(self) -> None:
        """Explicitly close the config store, releasing its resources.

        This is called automatically when using the config store as a context
        manager. If not called explicitly, resources will eventually be freed
        by the garbage collector.

        Note: Attempting to use the config store after it is closed will result
        in a trap.
        """
        self._store.__exit__(None, None, None)

    def __enter__(self) -> Self:
        """Context manager entry.

        Allows use of ConfigStore in a 'with' statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.

        Use of the context manager will free up the underlying host resource on
        exit. Referencing the resource after context manager exit will result in
        a trap.
        """
        self.close()
