"""WSGI adapter for Fastly Compute services.

This module provides utilities for running WSGI applications on Fastly Compute
by adapting between the Fastly WIT API and the WSGI specification.
"""

# The IDNA encoding is used by werkzeug (used by flask and others doing wsgi); without
# a top-level import componentize-py won't include the encoding in our final artifact
# and we get runtime LookupErrors when werkzeug tries to use the codec.
import encodings.idna  # noqa: F401
import sys
import traceback
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse
from wsgiref.types import InputStream

from wit_world.exports import HttpIncoming

from fastly_compute._bindings import async_io, http_body, http_req, http_resp
from fastly_compute._bindings.http_downstream import (
    NextRequestOptions,
    await_request,
    next_request,
)
from fastly_compute._bindings.http_resp import send_downstream
from fastly_compute.exceptions.types.error import CannotRead
from fastly_compute.utils import create_body_reader


def serve_wsgi_request(
    req: http_req.Request,
    body: InputStream,
    app: Callable,
    handle_errors: bool = False,
) -> None:
    """Serve a single WSGI request using the Fastly Compute API.

    This function adapts between Fastly's WIT-based HTTP API and the WSGI
    specification, allowing any WSGI-compatible web framework to run on
    Fastly Compute.

    :arg req: Fastly HTTP request object from WIT bindings
    :arg body: WSGI input stream containing the request body (PEP 3333 compliant)
    :arg app: WSGI application callable
    :arg handle_errors: If True, log exceptions and return 500; otherwise let
        the server or WSGI app handle them
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
        "wsgi.input": body,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": True,
        "SCRIPT_NAME": "",
        "CONTENT_TYPE": "",
        "CONTENT_LENGTH": "",
        "HTTP_HOST": url.netloc or "localhost",
    }

    # Add incoming HTTP headers to environ (WSGI spec requires HTTP_ prefix)
    # Use cursor-based iteration to read all header names
    cursor = 0
    while True:
        header_names_str, next_cursor = req.get_header_names(
            max_len=8192, cursor=cursor
        )
        if not header_names_str:
            break

        # Header names are NUL-separated
        header_names_split = (
            header_names_str.rstrip("\0").split("\0") if header_names_str else []
        )

        for header_name in header_names_split:
            if not header_name:
                continue

            # Get the header value
            header_value_bytes = req.get_header_value(header_name, max_len=8192)
            if header_value_bytes is None:
                continue

            # See https://peps.python.org/pep-3333/ - ISO-8859-1 encoding
            # should be used for bytes values across this boundary.
            header_value_str = header_value_bytes.decode("iso-8859-1")

            # Special handling for Content-Type and Content-Length (no HTTP_ prefix)
            if header_name.lower() == "content-type":
                environ["CONTENT_TYPE"] = header_value_str
            elif header_name.lower() == "content-length":
                environ["CONTENT_LENGTH"] = header_value_str
            else:
                # Convert to WSGI format: HTTP_ prefix, uppercase, hyphens to underscores
                wsgi_key = "HTTP_" + header_name.upper().replace("-", "_")
                environ[wsgi_key] = header_value_str

        # If there are more headers, continue with next cursor
        if next_cursor is None:
            break
        cursor = next_cursor

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
        http_body.write(error_body, error_message.encode())
        send_downstream(error_response, error_body)


class WsgiHttpIncoming(HttpIncoming):
    """HTTP request handler that serves WSGI applications.

    This class provides a convenient base class for serving WSGI applications
    on Fastly Compute. Instantiate this, and pass in your application.

    Example::

        from flask import Flask
        from fastly_compute.wsgi import WsgiHttpIncoming

        app = Flask(__name__)

        @app.route("/hello")
        def hello():
            return "Hello, World!"

        HttpIncoming = WsgiHttpIncoming(app)
    """

    def __init__(
        self,
        wsgi_app: Callable,
        handle_errors: bool = False,
        reuse_sandboxes_for_ms: int = 0,
    ):
        """Construct.

        :arg wsgi_app: The WSGI app to which to delegate requests
        :arg handle_errors: If True, log any raised exception and return a
            500-status response.
        :arg reuse_sandboxes_for_ms: If non-0, keep the sandbox alive for this
            many milliseconds to potentially serve additional requests.
        """
        self.wsgi_app = wsgi_app
        self.handle_errors = handle_errors
        self.reuse_sandboxes_for_ms = reuse_sandboxes_for_ms

    def __call__(self):
        """Return self to make the instance callable.

        This method makes the instance callable, which is required by the WSGI
        specification. WSGI expects the application to be a callable that returns
        itself when invoked without arguments.
        """
        return self

    def handle(self, request: http_req.Request, body: async_io.Pollable) -> None:  # pyrefly: ignore[bad-override]
        """Handle incoming HTTP requests by serving them through the WSGI app."""
        # The WIT export machinery passes raw resource handles; wrap them for
        # use with the _bindings API layer.
        request = http_req.Request(request)  # pyrefly: ignore[bad-argument-type]
        body = async_io.Pollable(body)  # pyrefly: ignore[bad-argument-type]
        with request:  # Ensure dropping of request resource before trying to get another one. This dodges a crash.
            serve_wsgi_request(
                request,
                create_body_reader(body),
                self.wsgi_app,
                handle_errors=self.handle_errors,
            )

        if not self.reuse_sandboxes_for_ms:
            return

        options = NextRequestOptions(timeout_ms=self.reuse_sandboxes_for_ms)
        while True:
            pending_request = next_request(options)
            try:
                result = await_request(pending_request)
            except CannotRead:
                # There were no more requests within the timeout.
                break
            else:
                if not result:
                    break
                request, body = result
                with request:
                    serve_wsgi_request(
                        request,
                        create_body_reader(body),
                        self.wsgi_app,
                        handle_errors=self.handle_errors,
                    )
