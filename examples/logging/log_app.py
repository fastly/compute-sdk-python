"""Logging example application.

Demonstrates Fastly Logging API usage with test endpoints.
"""

import json
import logging
import traceback
from typing import Any

from bottle import Bottle, response

from fastly_compute.log import FastlyLogHandler, LogEndpoint
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


# Direct API tests
@app.route("/test/write/<endpoint_name>/<message>")
@handle_request
def test_write(endpoint_name, message):
    """Test writing a string message."""
    endpoint = LogEndpoint.open(endpoint_name)
    endpoint.write(message)
    return {"written": True}


@app.route("/test/write-bytes/<endpoint_name>")
@handle_request
def test_write_bytes(endpoint_name):
    """Test writing bytes directly."""
    endpoint = LogEndpoint.open(endpoint_name)
    endpoint.write(b"Binary log data: \x00\x01\x02\x03")
    return {"written": True}


@app.route("/test/write-empty/<endpoint_name>")
@handle_request
def test_write_empty(endpoint_name):
    """Test writing an empty string."""
    endpoint = LogEndpoint.open(endpoint_name)
    endpoint.write("")
    return {"written": True}


@app.route("/test/context-manager/<endpoint_name>")
@handle_request
def test_context_manager(endpoint_name):
    """Test using endpoint as a context manager."""
    with LogEndpoint.open(endpoint_name) as endpoint:
        endpoint.write("Message from context manager")
    return {"success": True}


# Python logging integration tests
@app.route("/test/logging/<endpoint_name>/<level>/<message>")
@handle_request
def test_logging(endpoint_name, level, message):
    """Test standard Python logging integration."""
    logger = logging.getLogger(f"test_{endpoint_name}")
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    logger.handlers.clear()

    # Add Fastly handler with new API
    handler = FastlyLogHandler(default_endpoint=endpoint_name)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)

    # Log at the requested level
    log_func = getattr(logger, level.lower())
    log_func(message)

    # Clean up
    handler.close()

    return {"logged": True}


@app.route("/test/logging-extra/<endpoint_name>")
@handle_request
def test_logging_extra(endpoint_name):
    """Test logging with extra fields."""
    logger = logging.getLogger(f"test_extra_{endpoint_name}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = FastlyLogHandler(default_endpoint=endpoint_name)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s - user=%(user_id)s"
        )
    )
    logger.addHandler(handler)

    logger.info("User action", extra={"user_id": 12345})

    handler.close()

    return {"logged": True}


@app.route("/test/logging-multiple/<endpoint_name>")
@handle_request
def test_logging_multiple(endpoint_name):
    """Test logging multiple messages."""
    logger = logging.getLogger(f"test_multiple_{endpoint_name}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = FastlyLogHandler(default_endpoint=endpoint_name)
    logger.addHandler(handler)

    count = 5
    for i in range(count):
        logger.info(f"Log message {i + 1}")

    handler.close()

    return {"count": count}


@app.route("/test/json-log/<endpoint_name>")
@handle_request
def test_json_log(endpoint_name):
    """Test structured JSON logging."""
    logger = logging.getLogger(f"test_json_{endpoint_name}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = FastlyLogHandler(default_endpoint=endpoint_name)
    logger.addHandler(handler)

    # Create structured log message
    log_data = {
        "event": "request_processed",
        "status": 200,
        "duration_ms": 42,
        "user_id": 12345,
        "path": "/api/data",
    }
    logger.info(json.dumps(log_data))

    handler.close()

    return {"logged": True}


# Endpoint routing tests
@app.route("/test/logging-with-mapper/<logger_name>/<level>/<message>")
@handle_request
def test_logging_with_mapper(logger_name, level, message):
    """Test logging with endpoint mapper function."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # Define a mapper that routes based on logger name
    def endpoint_mapper(name: str) -> str | None:
        if name.startswith("api"):
            return "api-logs"
        # Return None to use default
        return None

    handler = FastlyLogHandler(
        default_endpoint="default-logs", endpoint_mapper=endpoint_mapper
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)

    # Log at the requested level
    log_func = getattr(logger, level.lower())
    log_func(message)

    handler.close()

    return {"logged": True}


@app.route("/test/logging-with-dict/<logger_name>/<level>/<message>")
@handle_request
def test_logging_with_dict(logger_name, level, message):
    """Test logging with dict-based endpoint mapper."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # Use a dict for simple mapping
    endpoint_map = {
        "api": "api-logs",
        "worker": "worker-logs",
        "background": "worker-logs",
    }

    handler = FastlyLogHandler(
        default_endpoint="default-logs",
        endpoint_mapper=lambda name: endpoint_map.get(name.split(".")[0]),
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)

    # Log at the requested level
    log_func = getattr(logger, level.lower())
    log_func(message)

    handler.close()

    return {"logged": True}


# Create the HTTP handler for Fastly Compute
HttpIncoming = WsgiHttpIncoming(app)
