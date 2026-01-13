# KV Store API Design

## Overview

Design for the KV Store API, providing access to Fastly's distributed key-value store for persistent data storage at the edge.

## WIT Interface Reference

```wit
interface kv-store {
  use types.{error, open-error};
  use http-body.{body};

  resource store {
    open: static func(name: string) -> result<store, open-error>;
    lookup: func(key: string) -> result<option<entry>, kv-error>;
    lookup-async: func(key: string) -> result<pending-lookup, error>;
    insert: func(key: string, body: body, options: insert-options) -> result<_, kv-error>;
    insert-async: func(key: string, body: body, options: insert-options) -> result<pending-insert, error>;
    delete: func(key: string) -> result<bool, kv-error>;
    delete-async: func(key: string) -> result<pending-delete, error>;
    %list: func(options: list-options) -> result<body, kv-error>;
    list-async: func(options: list-options) -> result<pending-list, error>;
  }

  resource entry {
    take-body: func() -> option<body>;
    metadata: func(max-len: u64) -> result<option<string>, error>;
    generation: func() -> u64;
  }

  enum insert-mode { overwrite, add, append, prepend }

  record insert-options {
    background-fetch: bool,
    if-generation-match: option<u64>,
    metadata: option<string>,
    time-to-live-sec: option<u32>,
    mode: insert-mode,
    extra: option<borrow<extra-insert-options>>,
  }

  enum list-mode { strong, eventual }

  record list-options {
    mode: list-mode,
    cursor: option<string>,
    limit: option<u32>,
    prefix: option<string>,
    extra: option<borrow<extra-list-options>>,
  }

  enum kv-error {
    bad-request, precondition-failed, payload-too-large,
    internal-error, too-many-requests, generic-error,
  }
}
```

Generated stubs: `stubs/wit_world/imports/kv_store.py`

## API Design

```python
from typing import Optional, Dict, Any, Iterator
from enum import Enum
from dataclasses import dataclass

class InsertMode(Enum):
    OVERWRITE = "overwrite"
    ADD = "add"
    APPEND = "append"
    PREPEND = "prepend"

class ListMode(Enum):
    STRONG = "strong"
    EVENTUAL = "eventual"

@dataclass
class InsertOptions:
    mode: InsertMode = InsertMode.OVERWRITE
    time_to_live_sec: Optional[int] = None
    metadata: Optional[str] = None
    if_generation_match: Optional[int] = None
    background_fetch: bool = False

@dataclass
class ListOptions:
    mode: ListMode = ListMode.STRONG
    cursor: Optional[str] = None
    limit: Optional[int] = None
    prefix: Optional[str] = None

class KVStoreEntry:
    @property
    def body(self) -> bytes: pass
    
    @property
    def text(self) -> str: pass
    
    def json(self) -> Any: pass
    
    @property
    def metadata(self) -> Optional[str]: pass
    
    @property
    def generation(self) -> int: pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

class KVStore:
    @classmethod
    def open(cls, name: str) -> 'KVStore': pass
    
    # Synchronous operations
    def lookup(self, key: str) -> Optional[KVStoreEntry]: pass
    
    def insert(self, key: str, value: bytes, options: Optional[InsertOptions] = None) -> None: pass
    
    def insert_text(self, key: str, text: str, options: Optional[InsertOptions] = None) -> None: pass
    
    def insert_json(self, key: str, data: Any, options: Optional[InsertOptions] = None) -> None: pass
    
    def delete(self, key: str) -> bool: pass
    
    def list(self, options: Optional[ListOptions] = None) -> 'KVStoreList': pass
    
    # Dict-like interface
    def __getitem__(self, key: str) -> bytes: pass
    def __setitem__(self, key: str, value: bytes) -> None: pass
    def __delitem__(self, key: str) -> None: pass
    def __contains__(self, key: str) -> bool: pass
    
    def get(self, key: str, default: Optional[bytes] = None) -> Optional[bytes]: pass
    def keys(self, prefix: Optional[str] = None) -> Iterator[str]: pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

class KVStoreList:
    def __iter__(self) -> Iterator[str]: pass
    @property
    def cursor(self) -> Optional[str]: pass

# Async variants
class AsyncKVStore(KVStore):
    async def lookup(self, key: str) -> Optional[KVStoreEntry]: pass
    async def insert(self, key: str, value: bytes, options: Optional[InsertOptions] = None) -> None: pass
    async def delete(self, key: str) -> bool: pass
    async def list(self, options: Optional[ListOptions] = None) -> 'KVStoreList': pass
```

## Usage Examples

```python
# Basic usage
from fastly_compute import KVStore

store = KVStore.open("my-store")

# Simple get/set
store["user:123"] = b"John Doe"

# Advanced insert
from fastly_compute import InsertMode, InsertOptions

options = InsertOptions(mode=InsertMode.ADD, time_to_live_sec=3600)
store.insert("session:abc", session_data, options)
```

## Deferred Features

- **Batch Operations**: Bulk insert/delete is not supported by the underlying API.
- **Complex Queries**: Only prefix listing is supported.
- **Transactions**: No multi-key transactions available.