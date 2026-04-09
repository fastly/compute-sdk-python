"""Config Store API for Fastly Compute

This module provides access to Fastly Config Stores, which allow you to store
configuration data that can be updated without redeploying your service.

Example::

    from fastly_compute.config_store import ConfigStore

    with ConfigStore.open("my-config") as config:
        api_url = config.get("api_url", "https://api.example.com")
"""

from fastly_compute._bindings.config_store import Store as _Store

# The maximum value for a u32, used to signal that we don't want to cap
# the length of values returned by the host.  In practice, this limit
# is at 8KB, though that could change.
_MAX_U32 = 0xFFFFFFFF


class ConfigStore(_Store):
    """Interface to Fastly Config Store.

    Config Stores provide read-only access to configuration data that can be
    updated without redeploying your service.

    Example::

        with ConfigStore.open("app-config") as config:
            api_url = config.get("api_url", "https://api.example.com")
    """

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
        result = super().get(key, _MAX_U32)
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
