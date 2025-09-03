"""Testing utilities for Fastly Compute integration tests.

This module provides pytest fixtures and base classes for testing
Fastly Compute services with viceroy.

To enable automatic viceroy output on test failures, add this to your conftest.py:

    pytest_plugins = ["fastly_compute.pytest_plugin"]
"""

import asyncio
import socket
import subprocess
import sys
from dataclasses import dataclass
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
    """Base class for viceroy integration tests.

    Provides common functionality for testing Fastly Compute services.
    Inherit from this class and use the viceroy_server fixture.

    Note: This assumes your WASM file is already built. Use your build system
    (e.g., Makefile) to ensure the WASM file is up to date before running tests.

    Example:
        ```python
        import pytest
        from fastly_compute.testing import ViceroyTestBase

        @pytest.mark.integration
        class TestMyService(ViceroyTestBase):
            def test_my_endpoint(self, viceroy_server):
                response = self.get("/my-endpoint", viceroy_server)
                assert response.status_code == 200
        ```
    """

    REQUEST_TIMEOUT = 10
    WASM_FILE = "app.wasm"  # Override this in subclasses if needed

    @staticmethod
    def _find_free_port() -> int:
        """Find an available port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            port = s.getsockname()[1]
        return port

    @pytest.fixture(scope="class")
    def viceroy_server(self) -> ViceroyServer:
        """Start viceroy server for the duration of the test class.

        Note: This assumes the WASM file already exists. Use your build system
        to ensure it's built before running tests.

        Returns:
            ViceroyServer: Server instance with process, base_url, and captured output
        """
        print("Starting viceroy server...")

        # Check if WASM file exists
        wasm_path = Path(self.WASM_FILE)
        if not wasm_path.exists():
            pytest.fail(
                f"WASM file '{self.WASM_FILE}' not found. Please build it first."
            )

        # Find an available port
        port = self._find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        output_lines = []  # Capture all output for debugging

        # Start viceroy process
        process = subprocess.Popen(
            ["viceroy", "serve", self.WASM_FILE, "--addr", f"127.0.0.1:{port}", "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        async def wait_for_ready():
            """Monitor process output for readiness signal."""
            timeout = 15  # Maximum wait time in seconds

            async def read_lines():
                """Async generator to read lines from stdout."""
                loop = asyncio.get_event_loop()
                while True:
                    # Read line in a thread to avoid blocking
                    line = await loop.run_in_executor(None, process.stdout.readline)
                    if not line:  # EOF
                        break
                    line_stripped = line.strip()
                    output_lines.append(line_stripped)  # Capture for debugging
                    yield line_stripped

            try:
                async with asyncio.timeout(timeout):
                    async for line in read_lines():
                        if "Listening on" in line:
                            print(f"Server ready: {line}")
                            return
                        # Check if process died
                        if process.poll() is not None:
                            raise RuntimeError(
                                "Viceroy process ended without starting server"
                            )

                    # If we get here, process ended without "Listening on"
                    raise RuntimeError("Viceroy process ended without starting server")

            except TimeoutError as e:
                process.terminate()
                process.wait()
                raise RuntimeError(
                    f"Viceroy server did not start within {timeout} seconds"
                ) from e

        # Wait for server to be ready
        try:
            asyncio.run(wait_for_ready())
        except RuntimeError as e:
            # Print captured output to stderr for debugging
            print(f"\nViceroy startup failed: {e}", file=sys.stderr)
            print("Viceroy output:", file=sys.stderr)
            for line in output_lines:
                print(f"  {line}", file=sys.stderr)
            pytest.fail(str(e))

        server = ViceroyServer(
            process=process, base_url=base_url, output_lines=output_lines
        )

        yield server

        # Cleanup: terminate the process
        print("Stopping viceroy server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def get(self, path: str, server: ViceroyServer, **kwargs) -> requests.Response:
        """Make a GET request to the viceroy server.

        Args:
            path: URL path to request
            server: ViceroyServer instance from fixture
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            requests.Response: The HTTP response
        """
        try:
            timeout = kwargs.pop("timeout", self.REQUEST_TIMEOUT)
            return requests.get(f"{server.base_url}{path}", timeout=timeout, **kwargs)
        except Exception as e:
            # On request failure, print viceroy output for debugging
            print(f"\nRequest to {server.base_url}{path} failed: {e}", file=sys.stderr)
            print("Recent viceroy output:", file=sys.stderr)
            # Show last 20 lines of output
            for line in server.output_lines[-20:]:
                print(f"  {line}", file=sys.stderr)
            raise

    def post(self, path: str, server: ViceroyServer, **kwargs) -> requests.Response:
        """Make a POST request to the viceroy server.

        Args:
            path: URL path to request
            server: ViceroyServer instance from fixture
            **kwargs: Additional arguments passed to requests.post()

        Returns:
            requests.Response: The HTTP response
        """
        try:
            timeout = kwargs.pop("timeout", self.REQUEST_TIMEOUT)
            return requests.post(f"{server.base_url}{path}", timeout=timeout, **kwargs)
        except Exception as e:
            # On request failure, print viceroy output for debugging
            print(
                f"\nPOST request to {server.base_url}{path} failed: {e}",
                file=sys.stderr,
            )
            print("Recent viceroy output:", file=sys.stderr)
            # Show last 20 lines of output
            for line in server.output_lines[-20:]:
                print(f"  {line}", file=sys.stderr)
            raise

    def request(
        self, method: str, path: str, server: ViceroyServer, **kwargs
    ) -> requests.Response:
        """Make an HTTP request to the viceroy server.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: URL path to request
            server: ViceroyServer instance from fixture
            **kwargs: Additional arguments passed to requests.request()

        Returns:
            requests.Response: The HTTP response
        """
        try:
            timeout = kwargs.pop("timeout", self.REQUEST_TIMEOUT)
            return requests.request(
                method, f"{server.base_url}{path}", timeout=timeout, **kwargs
            )
        except Exception as e:
            # On request failure, print viceroy output for debugging
            print(
                f"\n{method} request to {server.base_url}{path} failed: {e}",
                file=sys.stderr,
            )
            print("Recent viceroy output:", file=sys.stderr)
            # Show last 20 lines of output
            for line in server.output_lines[-20:]:
                print(f"  {line}", file=sys.stderr)
            raise


def create_viceroy_server_fixture(
    wasm_file: str = "app.wasm", scope: str = "class", timeout: int = 15
):
    """Factory function to create a viceroy server fixture with custom settings.

    Args:
        wasm_file: Name of the WASM file to serve (default: "app.wasm")
        scope: Pytest fixture scope (default: "class")
        timeout: Server startup timeout in seconds (default: 15)

    Returns:
        pytest fixture function

    Example:
        ```python
        from fastly_compute.testing import create_viceroy_server_fixture

        # Custom fixture for different WASM file
        my_server = create_viceroy_server_fixture("my-service.wasm")

        class TestMyService:
            def test_endpoint(self, my_server):
                # my_server is a ViceroyServer instance
                response = requests.get(f"{my_server.base_url}/test")
                assert response.status_code == 200
        ```
    """

    @pytest.fixture(scope=scope)
    def _viceroy_server_fixture():
        """Custom viceroy server fixture."""
        print(f"Starting viceroy server with {wasm_file}...")

        # Check if WASM file exists
        wasm_path = Path(wasm_file)
        if not wasm_path.exists():
            pytest.fail(f"WASM file '{wasm_file}' not found. Please build it first.")

        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            port = s.getsockname()[1]

        base_url = f"http://127.0.0.1:{port}"
        output_lines = []

        # Start viceroy process
        process = subprocess.Popen(
            ["viceroy", "serve", wasm_file, "--addr", f"127.0.0.1:{port}", "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        async def wait_for_ready():
            """Monitor process output for readiness signal."""

            async def read_lines():
                """Async generator to read lines from stdout."""
                loop = asyncio.get_event_loop()
                while True:
                    line = await loop.run_in_executor(None, process.stdout.readline)
                    if not line:
                        break
                    line_stripped = line.strip()
                    output_lines.append(line_stripped)
                    yield line_stripped

            try:
                async with asyncio.timeout(timeout):
                    async for line in read_lines():
                        if "Listening on" in line:
                            print(f"Server ready: {line}")
                            return
                        if process.poll() is not None:
                            raise RuntimeError(
                                "Viceroy process ended without starting server"
                            )
                    raise RuntimeError("Viceroy process ended without starting server")
            except TimeoutError as e:
                process.terminate()
                process.wait()
                raise RuntimeError(
                    f"Viceroy server did not start within {timeout} seconds"
                ) from e

        # Wait for server to be ready
        try:
            asyncio.run(wait_for_ready())
        except RuntimeError as e:
            print(f"\nViceroy startup failed: {e}", file=sys.stderr)
            print("Viceroy output:", file=sys.stderr)
            for line in output_lines:
                print(f"  {line}", file=sys.stderr)
            pytest.fail(str(e))

        server = ViceroyServer(
            process=process, base_url=base_url, output_lines=output_lines
        )

        yield server

        # Cleanup
        print("Stopping viceroy server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    return _viceroy_server_fixture
