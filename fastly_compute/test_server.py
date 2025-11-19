"""Local test server helper for backend testing.

Provides a simple HTTP server that can act as a backend for viceroy testing.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


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
    """Local HTTP server for backend testing.

    This server can be used to mock external backends during testing.
    It supports both httpbin-style behavior and custom response patterns.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        responses: dict[str, dict[str, Any]] | None = None,
    ):
        """Initialize the test server.

        Args:
            host: The host interface to bind to (default: "127.0.0.1")
            port: The port to bind to (default: 0 for auto-assignment)
            responses: Optional dict mapping paths to response configs.
                      Each response config can contain:
                      - "status": HTTP status code (default: 200)
                      - "headers": Dict of HTTP headers
                      - "body": Response body (dict will be JSON-encoded)
                      Example: {"/api/test": {"status": 200, "body": {"success": True}}}
        """
        self.host = host
        self.port = port
        self.responses = responses or {}
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> str:
        """Start the test server.

        Returns:
            The base URL of the started server (e.g., "http://127.0.0.1:12345")
        """
        if self.server is not None:
            raise RuntimeError("Server is already running")

        # Create server
        self.server = HTTPServer((self.host, self.port), TestRequestHandler)

        # Set responses on server for handler access
        self.server.responses = self.responses

        # Get actual port (important when port=0 for auto-assignment)
        actual_port = self.server.server_address[1]
        base_url = f"http://{self.host}:{actual_port}"

        # Start server in background thread
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        # Wait a bit for server to be ready
        time.sleep(0.1)

        return base_url

    def stop(self):
        """Stop the test server."""
        if self.server is None:
            return

        self.server.shutdown()
        self.server.server_close()
        self.server = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            self.thread = None

    def __enter__(self):
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    @property
    def base_url(self) -> str:
        """Get the base URL of the running server."""
        if self.server is None:
            raise RuntimeError("Server is not running")

        host, port = self.server.server_address
        return f"http://{host}:{port}"
