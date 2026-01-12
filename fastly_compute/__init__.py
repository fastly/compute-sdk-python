"""Fastly Compute SDK for Python.

This package provides a Python SDK for building Fastly Compute services.
"""

# Testing utilities are available but not imported by default
# Users can import them explicitly: from fastly_compute.testing import ViceroyTestBase

from fastly_compute.wit_patching.patches import patch

# Before anything from the fastly_compute package is used, do our monkeypatching
# to make the WIT-generated code act more Pythonically:
patch()
