"""WSGI adapter for Fastly Compute services.

This module provides utilities for running WSGI applications on Fastly Compute
by adapting between the Fastly WIT API and the WSGI specification.
"""

import sys
import traceback
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from wit_world.exports import HttpIncoming as WitHttpIncoming
from wit_world.imports import http_body, http_resp
from wit_world.imports.http_resp import send_downstream


def serve_wsgi_request(
    req: Any,
    body: Any,
    app: Callable,
    handle_errors: bool = False,
) -> None:
    """Serve a single WSGI request using the Fastly Compute API.

    This function adapts between Fastly's WIT-based HTTP API and the WSGI
    specification, allowing any WSGI-compatible web framework to run on
    Fastly Compute.

    Args:
        req: Fastly HTTP request object from WIT bindings
        body: Fastly HTTP body object from WIT bindings
        app: WSGI application callable
        handle_errors: If True, the wrapper will log exceptions and return 500; if not,
                       then it will be handled by the server (or will be handled by
                       the WSGI app/framework itself).
    """
    response = http_resp.Response.new()
    response_body = http_body.new()

    def write(body_data: bytes) -> None:
        """Write response body data (deprecated WSGI mechanism)."""
        http_body.write(response_body, body_data)

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any | None = None
    ) -> Callable[[bytes], None]:
        """WSGI start_response callable."""
        code, _description = status.split(" ", 1)
        response.set_status(int(code))
        for header, value in headers:
            response.append_header(header, value.encode())
        return write

    # Parse request URL
    url = urlparse(req.get_uri(2048))

    # Build WSGI environ dict
    environ = {
        "REQUEST_METHOD": req.get_method(12),
        "PATH_INFO": url.path,
        "QUERY_STRING": url.query,
        "SERVER_NAME": url.hostname or "localhost",
        "SERVER_PORT": str(url.port or 80),
        "wsgi.errors": sys.stderr,
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": url.scheme or "http",
        "wsgi.input": sys.stdin.buffer,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": True,
        "SCRIPT_NAME": "",
        "CONTENT_TYPE": "",
        "CONTENT_LENGTH": "",
        "HTTP_HOST": url.netloc or "localhost",
    }

    try:
        # Call the WSGI app and collect response body chunks
        for body_chunk in app(environ, start_response):
            # TODO: this would be a good place to stream, but for now we just
            #       write to the buffer and send once the handler is done.
            write(body_chunk)

        # Send the complete response downstream
        send_downstream(response, response_body)

    except Exception as e:
        if not handle_errors:
            raise

        print(f"Error in serve_wsgi_request: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

        # Send 500 error response
        error_response = http_resp.Response.new()
        error_body = http_body.new()
        error_response.set_status(500)
        error_response.append_header("content-type", b"text/plain")
        error_message = f"Internal Server Error: {e}"
        http_body.write(error_body, error_message.encode(), http_body.WriteEnd.BACK)
        send_downstream(error_response, error_body)


class WsgiHttpIncoming(WitHttpIncoming):
    """HTTP request handler that serves WSGI applications.

    This class provides a convenient base class for serving WSGI applications
    on Fastly Compute. Subclass this and set the `app` attribute to your WSGI
    application.

    Example:
        ```python
        from flask import Flask
        from fastly_compute.wsgi import WsgiHttpIncoming

        app = Flask(__name__)

        @app.route("/hello")
        def hello():
            return "Hello, World!"

        HttpIncoming = WsgiHttpIncoming(app)
        ```
    """

    def __init__(self, wsgi_app: Callable, handle_errors: bool = False):
        self.wsgi_app = wsgi_app
        self.handle_errors = handle_errors

    def __call__(self):
        return self

    def handle(self, request: Any, body: Any) -> None:
        """Handle incoming HTTP request by serving it through the WSGI app."""
        serve_wsgi_request(
            request,
            body,
            self.wsgi_app,
            handle_errors=self.handle_errors,
        )
