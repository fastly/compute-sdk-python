"""Example demonstrating interactions with backends via the requests facade"""

import json
import traceback
import typing
from typing import Any

from bottle import Bottle, request

import fastly_compute.requests as requests
from fastly_compute.wsgi import WsgiHttpIncoming

app = Bottle()


def _map_error(e: Exception):
    """Return a standardized error response.

    Args:
        e: The exception that occurred
        demo: The demo/endpoint name for this error
    """
    return {
        "error": repr(e),
        "error_type": type(e).__name__,
        "tb": traceback.format_exc(),
    }


def _proxy_request(method: str, url: str, **kwargs) -> dict[str, Any]:
    try:
        response = requests.request(method, url, **kwargs)
    except Exception as e:
        return _map_error(e)

    return {
        "method": method,
        "url": url,
        "backend": kwargs.get("backend"),
        "status_code": response.status_code,
        "success": response.ok,
        "headers_count": len(response.headers),
        "content_length": len(response.content),
        "response_preview": response.text[:200] + "..."
        if len(response.text) > 200
        else response.text,
    }


@app.route("/proxy/<method>")
def proxy(method: str):
    """Proxy endpoint for testing; pass through parameters.

    Don't deploy actual code that does this as it is likely
    to be abused if allowed to hit unrestricted domains.
    This proxy method is intended for testing use.
    """
    # Type checker doesn't quite understand bottle's DictProperty
    # so we need to give it hints.
    query = typing.cast(typing.Mapping[str, str], request.query)
    headers_dict = typing.cast(typing.Mapping[str, str], request.headers)

    url: str | None = query.get("url")
    if not url:
        return {"error": "url query parameter is required"}

    backend = query.get("backend")
    json_param = query.get("json")

    # Reconstitute JSON parameter if present
    json_data = None
    if json_param:
        try:
            json_data = json.loads(json_param)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in json parameter: {e}"}

    headers = {}
    for k, v in headers_dict.items():
        if k.lower() != "host":
            headers[k] = v

    return _proxy_request(
        method, url=url, backend=backend, json=json_data, headers=headers
    )


# Create the HTTP handler
HttpIncoming = WsgiHttpIncoming(app)
