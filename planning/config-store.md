# Config Store API Design

## Overview

Design for the Config Store API (and legacy Dictionary API), providing access to configuration key-value pairs.

## WIT Interface Reference

```wit
interface config-store {
  use types.{error, open-error};

  resource store {
    open: static func(name: string) -> result<store, open-error>;
    get: func(key: string, max-len: u64) -> result<option<string>, error>;
  }
}
```

Generated stubs: `stubs/wit_world/imports/config_store.py`

## API Design

```python
from typing import Optional, Any
import json

class ConfigStore:
    """Interface to Fastly Config Store (or Dictionary).
    
    Config Stores provide read-only access to configuration data
    that can be updated without redeploying code.
    """
    
    @classmethod
    def open(cls, name: str) -> 'ConfigStore':
        """Open a Config Store by name.
        
        Args:
            name: The name of the Config Store
            
        Returns:
            ConfigStore instance
            
        Raises:
            ValueError: If name is invalid  
            RuntimeError: If store doesn't exist
        """
        pass
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value.
        
        Args:
            key: The configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        pass
    
    def has(self, key: str) -> bool:
        """Check if a key exists in the config store.
        
        Args:
            key: The configuration key
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """Get a configuration value as an integer."""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default
    
    def get_bool(self, key: str, default: Optional[bool] = None) -> Optional[bool]:
        """Get a configuration value as a boolean.
        
        Recognizes: true/false, yes/no, 1/0, on/off (case-insensitive)
        """
        value = self.get(key)
        if value is None:
            return default
        
        lower = value.lower()
        if lower in ('true', 'yes', '1', 'on'):
            return True
        elif lower in ('false', 'no', '0', 'off'):
            return False
        else:
            return default
    
    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """Get a configuration value as a float."""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default
    
    def get_json(self, key: str, default: Any = None) -> Any:
        """Get a configuration value parsed as JSON."""
        value = self.get(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    
    # Dict-like interface
    
    def __getitem__(self, key: str) -> str:
        """Get value using dict syntax: value = config[key]"""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists: key in config"""
        return self.has(key)
    
    # Context manager
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Legacy alias
Dictionary = ConfigStore
```

## Usage Examples

```python
from fastly_compute import ConfigStore

# Open a config store
config = ConfigStore.open("app-config")

# Basic string access
api_url = config.get("api_url", "https://api.example.com")

# Type conversion helpers
max_retries = config.get_int("max_retries", default=3)
debug_mode = config.get_bool("debug", default=False)
timeout = config.get_float("timeout_sec", default=30.0)

# JSON configuration
features = config.get_json("features", default={
    "new_ui": False,
    "beta_api": False
})

# Dict-like access
if "feature_flag_x" in config:
    enabled = config.get_bool("feature_flag_x")
```

## Deferred Features

- **Environment Variable Fallback**: Explicitly out of scope. We follow the Rust/Go pattern of strictly wrapping the Config Store API.
- **Write Operations**: Config Stores are read-only at the edge.
- **Iteration**: Listing all keys is not supported by the underlying API.
