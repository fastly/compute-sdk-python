"""Testing utilities for Fastly Compute tests.

This module provides pytest fixtures and base classes for testing
Fastly Compute services with viceroy.

To enable automatic viceroy output on test failures, add this to your conftest.py:

    pytest_plugins = ["fastly_compute.pytest_plugin"]
"""

import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from os import environ
from pathlib import Path

import pytest
import requests


@dataclass
class ViceroyServer:
    """Represents a running viceroy server instance."""

    process: subprocess.Popen
    base_url: str
    output_lines: list[str]  # Capture output for debugging


class ViceroyTestBase:
    """Base class for viceroy tests.

    Provides common functionality for testing Fastly Compute services.
    Inherit from this class and use the viceroy_server fixture.

    Note: This assumes your WASM file is already built. Use your build system
    (e.g., Makefile) to ensure the WASM file is up to date before running tests.

    Example:
        ```python
        import pytest
        from fastly_compute.testing import ViceroyTestBase

        class TestMyService(ViceroyTestBase):
            def test_my_endpoint(self):
                response = self.get("/my-endpoint")
                assert response.status_code == 200
        ```
    """

    REQUEST_TIMEOUT = 10
    WASM_FILE = "build/bottle-app.composed.wasm"  # Default to the main example
    _server: ViceroyServer | None = None  # Will be set by the fixture

    @property
    def server(self) -> ViceroyServer:
        assert self._server is not None
        return self._server

    @staticmethod
    def _find_free_port() -> int:
        """Find an available port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            port = s.getsockname()[1]
        return port

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def viceroy_server(cls):
        """Start viceroy server for the duration of the test class.

        Note: This assumes the WASM file already exists. Use your build system
        to ensure it's built before running tests.

        Returns:
            ViceroyServer: Server instance with process, base_url, and captured output
        """
        print("Starting viceroy server...")

        # Check if WASM file exists
        wasm_path = Path(cls.WASM_FILE)
        if not wasm_path.exists():
            pytest.fail(
                f"WASM file '{cls.WASM_FILE}' not found. Please build it first."
            )

        # Find an available port
        port = cls._find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        output_lines: list[str] = []  # Capture all output for debugging
        output_lock = threading.Lock()
        stop_capture = threading.Event()

        # Start viceroy process
        process = subprocess.Popen(
            [
                environ.get("VICEROY", "viceroy"),
                "serve",
                cls.WASM_FILE,
                "--addr",
                f"127.0.0.1:{port}",
                "-v",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Start background thread to continuously capture output
        def capture_output_thread():
            """Continuously capture viceroy output throughout test execution."""
            assert process.stdout is not None, "stdout should be PIPE"
            while not stop_capture.is_set():
                line = process.stdout.readline()
                if not line:  # EOF
                    break
                with output_lock:
                    output_lines.append(line.strip())

        output_thread = threading.Thread(target=capture_output_thread, daemon=True)
        output_thread.start()

        # Wait for server to be ready
        timeout = 15
        start_time = time.monotonic()
        server_ready = False

        while time.monotonic() - start_time < timeout:
            if process.poll() is not None:
                # Process died, collect output and fail
                stop_capture.set()
                time.sleep(0.1)  # Give thread time to capture final output
                with output_lock:
                    all_output = "\n".join(output_lines)
                pytest.fail(f"Viceroy failed to start. Output:\n{all_output}")

            # Check if we've seen the "Listening on" message
            with output_lock:
                for line in output_lines:
                    if "Listening on" in line:
                        print(f"Server ready: {line}")
                        server_ready = True
                        break

            if server_ready:
                break

        if not server_ready:
            stop_capture.set()
            process.terminate()
            process.wait()
            with output_lock:
                all_output = "\n".join(output_lines)
            pytest.fail(
                f"Viceroy server did not start within {timeout} seconds. Output:\n{all_output}"
            )

        server = ViceroyServer(
            process=process, base_url=base_url, output_lines=output_lines
        )

        # Set the server as a class attribute so methods can access it
        cls._server = server

        yield server

        # Cleanup: stop output capture and terminate the process
        print("Stopping viceroy server...")
        stop_capture.set()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def get(self, path: str, **kwargs) -> requests.Response:
        """Make a GET request to the viceroy server.

        Args:
            path: URL path to request
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            requests.Response: The HTTP response
        """
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """Make a POST request to the viceroy server.

        Args:
            path: URL path to request
            **kwargs: Additional arguments passed to requests.post()

        Returns:
            requests.Response: The HTTP response
        """
        return self.request("POST", path, **kwargs)

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make an HTTP request to the viceroy server.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: URL path to request
            **kwargs: Additional arguments passed to requests.request()

        Returns:
            requests.Response: The HTTP response
        """
        timeout = kwargs.pop("timeout", self.REQUEST_TIMEOUT)
        response = requests.request(
            method, f"{self.server.base_url}{path}", timeout=timeout, **kwargs
        )
        return response
