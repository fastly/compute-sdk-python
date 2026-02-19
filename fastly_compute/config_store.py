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

from .resource import FastlyResource

# The maximum value for a u32, used to signal that we don't want to cap
# the length of values returned by the host.  In practice, this limit
# is at 8KB, though that could change.
_MAX_U32 = 0xFFFFFFFF


class ConfigStore(FastlyResource[wit_config_store.Store]):
    """Interface to Fastly Config Store.

    Config Stores provide read-only access to configuration data that can be
    updated without redeploying your service.

    Example::

        with ConfigStore.open("app-config") as config:
            api_url = config.get("api_url", "https://api.example.com")
    """

    def __init__(self, store: wit_config_store.Store):
        """Private constructor. Use ConfigStore.open() instead."""
        super().__init__(store)

    @classmethod
    def open(cls, name: str) -> Self:
        """Open a config store by name.

        :arg name: The name of the config store
        :return: ConfigStore instance
        :raise ~fastly_compute.exceptions.types.open_error.NotFound: If the config store doesn't exist
        :raise ~fastly_compute.exceptions.types.open_error.InvalidSyntax: If the name is invalid
        :raise ~fastly_compute.exceptions.types.open_error.NameTooLong: If the name is too long

        Example::

            config = ConfigStore.open("my-config")
        """
        store = wit_config_store.Store.open(name)
        return cls(store)

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a configuration value.

        :arg key: The configuration key
        :arg default: Default value if key not found
        :return: Configuration value or default if not found
        :raise ~fastly_compute.exceptions.types.error.InvalidArgument: If the key is invalid

        Example::

            config = ConfigStore.open("app-config")
            api_url = config.get("api_url", "https://api.example.com")
        """
        result = self._inner.get(key, _MAX_U32)
        if result is None:
            result = default

        return result

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the config store.

        :arg key: The configuration key
        :return: True if the key exists, False otherwise
        :raise ~fastly_compute.exceptions.types.error.InvalidArgument: If the key is invalid
        :raise KeyError: If the key is not a str

        Example::

            config = ConfigStore.open("app-config")
            if "feature_flag" in config:
                print("Feature flag exists")
        """
        if not isinstance(key, str):
            raise KeyError("Key must be a str")
        return self.get(key) is not None
