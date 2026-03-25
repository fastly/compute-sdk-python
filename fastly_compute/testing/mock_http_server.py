"""Local test server helper for backend testing.

Provides a simple HTTP server that can act as a backend for viceroy testing.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


class _BaseTestRequestHandler(BaseHTTPRequestHandler):
    """Base HTTP request handler for test server.

    This is a template class - use make_test_request_handler() to create
    a handler with specific responses configured.
    """

    # This will be overridden in subclasses created by the factory
    configured_responses: dict[str, dict[str, Any]] = {}

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
        responses = self.configured_responses
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


def make_test_request_handler(
    responses: dict[str, dict[str, Any]],
) -> type[BaseHTTPRequestHandler]:
    """Create a request handler class with configured responses.

    :arg responses: Dictionary mapping paths to response configurations
    :return: A new handler class with responses bound as a class attribute
    """
    # Create a new class that inherits from our base handler
    # and sets the responses as a class attribute
    return type(
        "TestRequestHandler",
        (_BaseTestRequestHandler,),
        {"configured_responses": responses},
    )


class MockHttpServer:
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

        :arg host: The host interface to bind to (default: "127.0.0.1")
        :arg port: The port to bind to (default: 0 for auto-assignment)
        :arg responses: Optional dict mapping paths to response configs.
            Each response config can contain...

            "status"
                HTTP status code (default: 200)
            "headers"
                Dict of HTTP headers
            "body"
                Response body (dict will be JSON-encoded)

            Example::

                {"/api/test": {"status": 200, "body": {"success": True}}}
        """
        self.host = host
        self.port = port
        self.responses = responses or {}
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        """Start the test server.

        :return: The base URL of the started server (e.g., "http://127.0.0.1:12345")
        """
        if self._server is not None:
            raise RuntimeError("Server is already running")

        # Create a handler class with our responses configured
        handler_class = make_test_request_handler(self.responses)

        # Create server
        self._server = HTTPServer((self.host, self.port), handler_class)

        # Get actual port (important when port=0 for auto-assignment)
        # server_address returns (host, port) for IPv4, or (host, port, flowinfo, scopeid) for IPv6
        actual_port = self._server.server_address[1]  # Port is always at index 1
        base_url = f"http://{self.host}:{actual_port}"

        # Start server in background thread
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        # Wait a bit for server to be ready
        time.sleep(0.1)

        return base_url

    def stop(self):
        """Stop the test server."""
        if self._server is None:
            return

        self._server.shutdown()
        self._server.server_close()
        self._server = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

    def __enter__(self):
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    @property
    def base_url(self) -> str:
        """Get the base URL of the running server."""
        if self._server is None:
            raise RuntimeError("Server is not running")

        # Port is always at index 1 regardless of address family
        port = self._server.server_address[1]
        return f"http://{self.host}:{port}"
