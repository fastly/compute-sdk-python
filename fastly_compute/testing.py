"""Testing utilities for Fastly Compute tests.

This module provides pytest fixtures and base classes for testing
Fastly Compute services with viceroy.

To enable automatic viceroy output on test failures, add this to your conftest.py:

    pytest_plugins = ["fastly_compute.pytest_plugin"]
"""

import os
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
import requests
import tomli_w


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
    WASM_FILE = "build/wit-bottle.wasm"  # Default to the main example
    server: ViceroyServer = None  # Will be set by the fixture

    # Configuration for backend testing
    VICEROY_CONFIG = None  # Dict with viceroy config, or None for no config
    _config_file_path = None  # Will store temp config file path

    @staticmethod
    def _find_free_port() -> int:
        """Find an available port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            port = s.getsockname()[1]
        return port

    @classmethod
    def _create_viceroy_config(cls, backends: dict[str, str] | None = None) -> str:
        """
        Create a temporary viceroy configuration file.

        Args:
            backends: Dict mapping backend names to URLs
                     e.g., {"httpbin": "http://127.0.0.1:8080"}

        Returns:
            Path to the temporary configuration file
        """
        config_dict = {}

        # Add backends if provided
        if backends:
            config_dict["local_server"] = {
                "backends": {name: {"url": url} for name, url in backends.items()}
            }

        # Add any additional config from class
        if cls.VICEROY_CONFIG:
            # Merge with class config
            if "local_server" in config_dict and "local_server" in cls.VICEROY_CONFIG:
                # Merge local_server sections
                for key, value in cls.VICEROY_CONFIG["local_server"].items():
                    if key == "backends" and "backends" in config_dict["local_server"]:
                        # Merge backends
                        config_dict["local_server"]["backends"].update(value)
                    else:
                        config_dict["local_server"][key] = value
            else:
                # Add other sections
                config_dict.update(cls.VICEROY_CONFIG)

        # Generate TOML content
        toml_content = tomli_w.dumps(config_dict)

        # Create temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".toml", prefix="viceroy_config_")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(toml_content)
        except:
            os.close(fd)  # Close if write failed
            raise

        return temp_path

    @classmethod
    def setup_backends(cls, backends: dict[str, str]):
        """
        Set up backends for testing.

        Call this in setUpClass or as a class-level setup.

        Args:
            backends: Dict mapping backend names to URLs
                     e.g., {"httpbin": "http://127.0.0.1:8080"}
        """
        cls._test_backends = backends

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def viceroy_server(cls) -> ViceroyServer:
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
        output_lines = []  # Capture all output for debugging
        output_lock = threading.Lock()
        stop_capture = threading.Event()

        # Create config file if needed
        config_file_path = None
        if hasattr(cls, "_test_backends") or cls.VICEROY_CONFIG:
            # Get backends from test setup (if any)
            backends = getattr(cls, "_test_backends", None)
            config_file_path = cls._create_viceroy_config(backends)
            cls._config_file_path = config_file_path

        # Build viceroy command
        viceroy_cmd = [
            "viceroy",
            "serve",
            cls.WASM_FILE,
            "--addr",
            f"127.0.0.1:{port}",
            "-v",
        ]
        if config_file_path:
            viceroy_cmd.extend(["-C", config_file_path])

        # Start viceroy process
        process = subprocess.Popen(
            viceroy_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Start background thread to continuously capture output
        def capture_output_thread():
            """Continuously capture viceroy output throughout test execution."""
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
        cls.server = server

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

        # Clean up config file if we created one
        if cls._config_file_path and os.path.exists(cls._config_file_path):
            try:
                os.unlink(cls._config_file_path)
            except OSError:
                pass  # Ignore cleanup errors
            cls._config_file_path = None

    def get(self, path: str, **kwargs) -> requests.Response:
        """Make a GET request to the viceroy server.

        Args:
            path: URL path to request
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            requests.Response: The HTTP response
        """
        timeout = kwargs.pop("timeout", self.REQUEST_TIMEOUT)
        response = requests.get(
            f"{self.server.base_url}{path}", timeout=timeout, **kwargs
        )
        return response

    def post(self, path: str, **kwargs) -> requests.Response:
        """Make a POST request to the viceroy server.

        Args:
            path: URL path to request
            **kwargs: Additional arguments passed to requests.post()

        Returns:
            requests.Response: The HTTP response
        """
        timeout = kwargs.pop("timeout", self.REQUEST_TIMEOUT)
        response = requests.post(
            f"{self.server.base_url}{path}", timeout=timeout, **kwargs
        )
        return response

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
