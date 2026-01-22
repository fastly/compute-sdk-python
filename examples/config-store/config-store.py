"""Config Store example application.

Demonstrates Fastly Config Store usage with minimal test endpoints.
"""

import json
import traceback
from typing import Any

from bottle import Bottle, response

from fastly_compute.config_store import ConfigStore
from fastly_compute.wsgi import WsgiHttpIncoming

app = Bottle()


def json_response(data: dict[str, Any], status_code: int = 200) -> str:
    """Create a JSON response."""
    response.content_type = "application/json"
    response.status = status_code
    return json.dumps(data, indent=2)


def handle_request(handler):
    """Decorator to handle common request/response patterns."""

    def wrapper(*args, **kwargs):
        try:
            result = handler(*args, **kwargs)
            return json_response(result)
        except Exception as e:
            return json_response(
                {
                    "error": repr(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                status_code=500,
            )

    return wrapper


@app.route("/get/<store_name>/<key>")
@app.route("/get/<store_name>/<key>/<default>")
@handle_request
def test_get(store_name, key, default=None):
    """Proxy endpoint to issue ConfigStore gets with optional default."""
    with ConfigStore.open(store_name) as config:
        value = config.get(key, default)
    return {"value": value}


@app.route("/get_with_initial_buf_len/<store_name>/<key>/<initial_buf_len:int>")
@handle_request
def test_get_with_initial_buf_len(store_name, key, initial_buf_len):
    """Proxy endpoint to test get with custom initial_buf_len using raw API."""
    config = ConfigStore.open(store_name)
    # Use _get_raw to test buffer sizing without automatic retry
    value = config._get_raw(key, initial_buf_len)
    return {"value": value}


@app.route("/contains/<store_name>/<key>")
@handle_request
def test_contains(store_name, key):
    """Proxy endpoint to test contains."""
    config = ConfigStore.open(store_name)
    contains = config.contains(key)
    return {"contains": contains}


# Create the HTTP handler for Fastly Compute
HttpIncoming = WsgiHttpIncoming(app)
