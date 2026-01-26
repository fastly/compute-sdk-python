import sys

from flask import Flask, request
from wit_world.imports import compute_runtime

from fastly_compute.wsgi import WsgiHttpIncoming

# Create Flask app
app = Flask(__name__)


@app.route("/hello/<name>")
def hello(name):
    return f"Hello {name}!"


@app.route("/info")
def info():
    """Return JSON with request information we can test against"""
    # Get some runtime info we can test
    vcpu_time = compute_runtime.get_vcpu_ms()

    return {
        "service": "fastly-compute-python-flask",
        "status": "ok",
        "message": "Hello from Fastly Compute with Flask!",
        "vcpu_time_ms": vcpu_time,
        "request_method": request.environ.get("REQUEST_METHOD"),
        "path_info": request.environ.get("PATH_INFO"),
        "python_version": sys.version,
        "request_headers": dict(request.headers),
    }


@app.route("/error")
def error():
    """Endpoint that intentionally raises an exception to test error handling."""
    raise RuntimeError("This is an intentional error for testing purposes")


# Create the HTTP handler using the shared WSGI infrastructure
HttpIncoming = WsgiHttpIncoming(app)
