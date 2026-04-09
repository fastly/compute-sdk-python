"""Generator for the fastly_compute/exceptions/ hierarchy.

Reads WIT via wasm-tools and generates Python exception classes for every
result error type in the Fastly Compute API, inheriting names and docstrings
from the WIT.

Generation is informed by the WIT JSON rather than componentize-py's generated
stubs — the JSON approach is more reliable since stubs lose type relationship
information (e.g. which errors each function can actually return).

This runs at SDK-build time; customers don't run it.
"""
