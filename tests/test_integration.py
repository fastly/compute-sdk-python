"""Integration tests for the Fastly Compute Python service."""

import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue

import pytest
import requests


@dataclass
class ViceroyServer:
    """Represents a running viceroy server instance."""

    process: subprocess.Popen
    base_url: str


@pytest.mark.integration
class TestFastlyComputeService:
    """Integration tests for the Fastly Compute service running under viceroy."""

    REQUEST_TIMEOUT = 10

    @staticmethod
    def _find_free_port() -> int:
        """Find an available port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    @pytest.fixture(scope="class", autouse=True)
    def build_service(self):
        """Build the WebAssembly component before running tests."""
        print("Building WebAssembly component...")
        result = subprocess.run(
            ["make", "app.wasm"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"Failed to build service: {result.stderr}")

    @pytest.fixture(scope="class")
    def viceroy_server(self):
        """Start viceroy server for the duration of the test class."""
        print("Starting viceroy server...")

        # Find an available port
        port = self._find_free_port()
        base_url = f"http://127.0.0.1:{port}"

        # Start viceroy in the background with the specific port and verbose output
        process = subprocess.Popen(
            ["viceroy", "serve", "app.wasm", "--addr", f"127.0.0.1:{port}", "-v"],
            cwd=Path(__file__).parent.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout for easier monitoring
            text=True,
        )

        # Use a queue to communicate between threads; this extra work is mostly
        # so that we have a solution that will work well enough on windows.
        output_queue = Queue()

        def read_output():
            """Read process output in a separate thread."""
            try:
                for line in iter(process.stdout.readline, ""):
                    output_queue.put(line.strip())
                    if not line:
                        break
            except Exception:
                pass

        # Start the output reading thread
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()

        # Wait for server to start by monitoring output
        timeout = 15  # Maximum wait time in seconds
        start_time = time.time()
        server_ready = False

        while time.time() - start_time < timeout:
            # Check if process is still running
            if process.poll() is not None:
                # Collect any remaining output
                remaining_lines = []
                try:
                    while True:
                        line = output_queue.get_nowait()
                        remaining_lines.append(line)
                except Empty:
                    pass
                all_output = "\n".join(remaining_lines)
                pytest.fail(f"Viceroy failed to start. Output:\n{all_output}")

            # Check for output indicating server is ready
            try:
                line = output_queue.get(timeout=0.1)
                if "Listening on" in line:
                    print(f"Server ready: {line}")
                    server_ready = True
                    break
            except Empty:
                continue

        if not server_ready:
            process.terminate()
            pytest.fail(f"Viceroy server did not start within {timeout} seconds")

        yield ViceroyServer(process=process, base_url=base_url)

        # Cleanup: terminate the process
        print("Stopping viceroy server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    def _get(self, path: str, server: ViceroyServer) -> requests.Response:
        """Make a GET request to the service."""
        return requests.get(f"{server.base_url}{path}", timeout=self.REQUEST_TIMEOUT)

    def test_hello_endpoint(self, viceroy_server):
        """Test the hello endpoint returns expected content."""
        response = self._get("/hello/test", viceroy_server)

        assert response.status_code == 200
        assert response.text == "Hello test!"

    def test_hello_endpoint_with_different_name(self, viceroy_server):
        """Test the hello endpoint with a different name parameter."""
        response = self._get("/hello/world", viceroy_server)

        assert response.status_code == 200
        assert response.text == "Hello world!"

    def test_info_endpoint(self, viceroy_server):
        """Test the info endpoint returns expected JSON with WIT data."""
        response = self._get("/info", viceroy_server)

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")

        data = response.json()

        # Check basic service info
        assert data["service"] == "fastly-compute-python"
        assert data["status"] == "ok"
        assert "message" in data

        # Check WIT API data
        assert "vcpu_time_ms" in data
        assert isinstance(data["vcpu_time_ms"], int)

        # Check request data
        assert data["request_method"] == "GET"
        assert data["path_info"] == "/info"

    def test_nonexistent_endpoint(self, viceroy_server):
        """Test that nonexistent endpoints return 404."""
        response = self._get("/nonexistent", viceroy_server)

        assert response.status_code == 404
