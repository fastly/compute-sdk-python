from urllib.parse import urlparse

from bottle import Bottle
from wit_world.exports import HttpIncoming as BaseHttpIncoming
from wit_world.imports import http_body, http_resp, log
from wit_world.imports.http_resp import send_downstream

# Enable a bit more debug logging from the framework.
app = Bottle()
app.catchall = False  # bottle backtrace causes issues; use our own.


@app.route("/hello/<name>")
def hello(name):
    return f"Hello {name}!"


@app.route("/info")
def info():
    """Return JSON with request information we can test against"""
    from bottle import request

    # Get some runtime info we can test
    vcpu_time = None
    try:
        from wit_world.imports import compute_runtime

        vcpu_time = compute_runtime.get_vcpu_ms()
    except Exception:
        pass

    return {
        "service": "fastly-compute-python",
        "status": "ok",
        "message": "Hello from Fastly Compute!",
        "vcpu_time_ms": vcpu_time,
        "request_method": request.environ.get("REQUEST_METHOD"),
        "path_info": request.environ.get("PATH_INFO"),
    }


def print(*args):
    # hack to allow print locally; so far, monkeypatching
    # sys.stdout/sys.stderr hasn't panned out, so more
    # research required.
    log_ep.write(" ".join(args).encode())


def init():
    global log_ep
    log_ep = log.Endpoint.get("")


class StdErr:
    """File-like object to receive errors and direct them to our logging endpoint"""

    def write(self, data: str):
        print(f"wsgi-error: {data}")

    def flush(self):
        pass


def serve_wsgi_request(req, body, app):
    """Pass a WSGI application a single request, and adapt its behavior back
    to the Fastly API."""

    response = http_resp.Response.new()
    response_body = http_body.new()

    def write(body_data: bytes):
        """Implement a mostly deprecated alternative body-writing mechanism of
        WSGI."""
        http_body.write(response_body, body_data, http_body.WriteEnd.BACK)

    def start_response(status: str, headers: list[tuple], exc_info=None):
        code, _description = status.split(" ", 1)
        response.set_status(int(code))
        for header, value in headers:
            response.append_header(header, value.encode())
        return write

    url = urlparse(req.get_uri(2048))
    environ = {
        "REQUEST_METHOD": req.get_method(12),
        "PATH_INFO": url.path,
        "QUERY_STRING": url.query,
        "SERVER_NAME": url.hostname,
        "SERVER_PORT": str(url.port),
        "wsgi.errors": StdErr(),
    }
    for body_chunk in app(environ, start_response):
        # TODO: this would be a good place to stream, but for now we just
        #       write to the buffer and send once the handler is done.
        write(body_chunk)
    send_downstream(response, response_body)


class HttpIncoming(BaseHttpIncoming):
    def handle(self, request, body):
        init()
        try:
            serve_wsgi_request(request, body, app)
        except Exception as e:
            log_exception(e)


def log_exception(e):
    """Pretty-print an exception to our logging endpoint.

    Do it without callling format_exc(), which calls stat() to determine whether
    we're in a tty and what its width is. stat() and other fd routines currently
    crash when they try to access stdout or stderr, probably because they are
    not in the preopens.
    """
    try:
        print(f"Exception {type(e).__name__} - {e}")
        print("--- Traceback Follows ---")

        current_tb = e.__traceback__
        while current_tb:
            frame = current_tb.tb_frame
            print(
                f"  File: {frame.f_code.co_filename}, "
                f"Function: {frame.f_code.co_name}, "
                f"Line: {frame.f_lineno}"
            )
            current_tb = current_tb.tb_next
    except Exception as e2:
        print(f"print_exc failed {e2}")
