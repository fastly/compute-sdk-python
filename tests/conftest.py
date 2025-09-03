"""Pytest configuration for Fastly Compute integration tests."""

# Enable the fastly_compute pytest plugin for automatic viceroy output on failures
pytest_plugins = ["fastly_compute.pytest_plugin"]
