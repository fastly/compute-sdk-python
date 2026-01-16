import typing

from bottle import Bottle, request
from wit_world.imports import compute_runtime

from fastly_compute.wsgi import WsgiHttpIncoming

print("DEBUG: bottle_app initialized")

# Enable a bit more debug logging from the framework.
app = Bottle()


@app.route("/hello/<name>")
def hello(name):
    return f"Hello {name}!"


@app.route("/info")
def info():
    """Return JSON with request information we can test against"""
    # Get some runtime info we can test
    vcpu_time = compute_runtime.get_vcpu_ms()

    # type checker doesn't quite understand bottle's DictProperty
    # so we need to give it a hint.
    headers = typing.cast(typing.Mapping[str, str], request.headers)

    return {
        "service": "fastly-compute-python",
        "status": "ok",
        "message": "Hello from Fastly Compute!",
        "vcpu_time_ms": vcpu_time,
        "request_method": request.environ.get("REQUEST_METHOD"),
        "path_info": request.environ.get("PATH_INFO"),
        "request_headers": dict(headers),
    }


@app.route("/error")
def error():
    """Endpoint that intentionally raises an exception to test error handling."""
    raise RuntimeError("This is an intentional error for testing purposes")


# Create the HTTP handler using the shared WSGI infrastructure
# Use basic environ for Bottle (doesn't need enhanced WSGI variables like Flask)
HttpIncoming = WsgiHttpIncoming(app, handle_errors=True)
