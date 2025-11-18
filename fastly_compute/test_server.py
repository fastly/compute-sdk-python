"""Local test server helper for backend testing.

Provides a simple HTTP server that can act as a backend for viceroy testing.
"""

import json
import socket
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass
class LocalTestServerConfig:
    """Configuration for test server."""

    host: str = "127.0.0.1"
    port: int = 0  # 0 = auto-assign port
    responses: dict[str, dict[str, Any]] = None

    def __post_init__(self):
        """Initialize responses to empty dict if not provided."""
        if self.responses is None:
            self.responses = {}


class TestRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for test server."""

    def do_GET(self):
        """Handle GET requests."""
        self._handle_request("GET")

    def do_POST(self):
        """Handle POST requests."""
        self._handle_request("POST")

    def do_PUT(self):
        """Handle PUT requests."""
        self._handle_request("PUT")

    def do_DELETE(self):
        """Handle DELETE requests."""
        self._handle_request("DELETE")

    def _handle_request(self, method: str):
        """Generic request handler."""
        # Parse request
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Read request body for POST/PUT
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        # Check if we have a configured response for this path
        responses = getattr(self.server, "responses", {})
        if path in responses:
            configured_response = responses[path]
            status = configured_response.get("status", 200)
            headers = configured_response.get("headers", {})
            response_body = configured_response.get("body", {})
        else:
            # Default httpbin-like response
            status = 200
            headers = {"Content-Type": "application/json"}

            # Create httpbin-like response
            request_headers = dict(self.headers)

            response_body = {
                "args": {
                    k: v[0] if len(v) == 1 else v for k, v in query_params.items()
                },
                "headers": request_headers,
                "origin": self.client_address[0],
                "url": f"http://{self.headers.get('Host', 'localhost')}{self.path}",
                "method": method,
                "path": path,
            }

            # Add body data for POST/PUT
            if body:
                try:
                    # Try to parse as JSON
                    json_data = json.loads(body.decode("utf-8"))
                    response_body["json"] = json_data
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Store as raw data
                    response_body["data"] = body.decode("utf-8", errors="replace")

        # Send response
        self.send_response(status)

        # Set headers
        if isinstance(headers, dict):
            for header_name, header_value in headers.items():
                self.send_header(header_name, header_value)

        # Default content-type if not set
        if "Content-Type" not in headers:
            self.send_header("Content-Type", "application/json")

        self.end_headers()

        # Send body
        if isinstance(response_body, dict | list):
            response_json = json.dumps(response_body, indent=2)
            self.wfile.write(response_json.encode("utf-8"))
        else:
            self.wfile.write(str(response_body).encode("utf-8"))

    def log_message(self, format, *args):
        """Override to reduce log noise in tests."""


class LocalTestServer:
    """Local HTTP server for backend testing."""

    def __init__(self, config: LocalTestServerConfig | None = None):
        """Construct a new test server."""
        self.config = config or LocalTestServerConfig()
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None
        self._running = False

    def start(self) -> str:
        """Start the test server.

        Returns:
            The base URL of the started server (e.g., "http://127.0.0.1:12345")
        """
        if self._running:
            raise RuntimeError("Server is already running")

        # Create server
        self.server = HTTPServer(
            (self.config.host, self.config.port), TestRequestHandler
        )

        # Set responses on server for handler access
        self.server.responses = self.config.responses

        # Get actual port (important when port=0 for auto-assignment)
        actual_port = self.server.server_address[1]
        base_url = f"http://{self.config.host}:{actual_port}"

        # Start server in background thread
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self._running = True

        # Wait a bit for server to be ready
        time.sleep(0.1)

        return base_url

    def stop(self):
        """Stop the test server."""
        if not self._running:
            return

        if self.server:
            self.server.shutdown()
            self.server.server_close()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        self._running = False

    def __enter__(self):
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    @property
    def base_url(self) -> str:
        """Get the base URL of the running server."""
        if not self._running or not self.server:
            raise RuntimeError("Server is not running")

        host, port = self.server.server_address
        return f"http://{host}:{port}"


def find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]
    return port


# Convenience functions for common test server patterns
def create_httpbin_server(host: str = "127.0.0.1", port: int = 0) -> LocalTestServer:
    """Create a server that mimics httpbin.org behavior."""
    config = LocalTestServerConfig(host=host, port=port)
    return LocalTestServer(config)


def create_mock_server(
    responses: dict[str, dict[str, Any]], host: str = "127.0.0.1", port: int = 0
) -> LocalTestServer:
    """Create a server with predefined responses.

    Args:
        responses: Dict mapping paths to response configs.
        host: The host to bind to.
        port: The port to bind to.
    """
    config = LocalTestServerConfig(host=host, port=port, responses=responses)
    return LocalTestServer(config)
