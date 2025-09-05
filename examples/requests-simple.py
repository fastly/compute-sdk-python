"""
Simple Requests Demo - Example using fastly_compute.requests with Bottle

This example demonstrates the requests-compatible HTTP client for making
backend requests in Fastly Compute using Bottle (which has fewer dependencies than Flask).
"""

from bottle import Bottle
from wit_world.imports import compute_runtime

# Import Fastly Compute modules
import fastly_compute.requests as requests
from fastly_compute.wsgi import WsgiHttpIncoming

app = Bottle()


@app.route("/static-get")
def static_get():
    """Demo GET request using static backend."""
    try:
        # Use static backend (requires 'httpbin' backend in viceroy.toml)
        response = requests.get("/get", backend="httpbin")

        return {
            "demo": "static-get",
            "backend_type": "static",
            "backend_name": "httpbin",
            "status_code": response.status_code,
            "success": response.ok,
            "url": response.url,
            "headers_count": len(response.headers),
            "content_length": len(response.content),
            "response_preview": response.text[:200] + "..."
            if len(response.text) > 200
            else response.text,
        }
    except Exception as e:
        return {"demo": "static-get", "error": str(e), "error_type": type(e).__name__}


@app.route("/static-post")
def static_post():
    """Demo POST request using static backend."""
    try:
        # POST JSON data to static backend
        post_data = {
            "message": "Hello from Fastly Compute!",
            "demo": "static-post",
            "vcpu_time": compute_runtime.get_vcpu_ms(),
        }

        response = requests.post("/post", backend="httpbin", json=post_data)

        return {
            "demo": "static-post",
            "backend_type": "static",
            "backend_name": "httpbin",
            "status_code": response.status_code,
            "success": response.ok,
            "sent_data": post_data,
            "content_length": len(response.content),
            "response_preview": response.text[:200] + "..."
            if len(response.text) > 200
            else response.text,
        }
    except Exception as e:
        return {"demo": "static-post", "error": str(e), "error_type": type(e).__name__}


@app.route("/dynamic-get")
def dynamic_get():
    """Demo GET request using dynamic backend."""
    try:
        # Make request to external service (creates dynamic backend)
        response = requests.get(
            "https://httpbin.org/get",
            headers={"User-Agent": "FastlyCompute-SimpleDemo/1.0"},
        )

        return {
            "demo": "dynamic-get",
            "backend_type": "dynamic",
            "target_url": "https://httpbin.org/get",
            "status_code": response.status_code,
            "success": response.ok,
            "url": response.url,
            "headers": dict(list(response.headers.items())[:5]),  # Show first 5 headers
            "content_length": len(response.content),
            "response_preview": response.text[:200] + "..."
            if len(response.text) > 200
            else response.text,
        }
    except Exception as e:
        return {"demo": "dynamic-get", "error": str(e), "error_type": type(e).__name__}


@app.route("/dynamic-post")
def dynamic_post():
    """Demo POST request using dynamic backend."""
    try:
        # POST to external service
        post_data = {
            "service": "fastly-compute",
            "demo": "dynamic-post",
            "timestamp": compute_runtime.get_vcpu_ms(),
            "message": "Dynamic backend POST from Fastly Compute",
        }

        response = requests.post(
            "https://httpbin.org/post",
            json=post_data,
            headers={
                "User-Agent": "FastlyCompute-SimpleDemo/1.0",
                "X-Demo": "fastly-compute-requests",
            },
        )

        return {
            "demo": "dynamic-post",
            "backend_type": "dynamic",
            "target_url": "https://httpbin.org/post",
            "status_code": response.status_code,
            "success": response.ok,
            "sent_data": post_data,
            "content_length": len(response.content),
            "response_preview": response.text[:200] + "..."
            if len(response.text) > 200
            else response.text,
        }
    except Exception as e:
        return {"demo": "dynamic-post", "error": str(e), "error_type": type(e).__name__}


@app.route("/error-demo")
def error_demo():
    """Demo error handling scenarios."""
    results = []

    # Test case 1: Invalid static backend
    try:
        response = requests.get("/test", backend="nonexistent-backend")
        results.append(
            {
                "test": "invalid-static-backend",
                "status": "unexpected_success",
                "status_code": response.status_code,
            }
        )
    except Exception as e:
        results.append(
            {
                "test": "invalid-static-backend",
                "status": "expected_error",
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )

    # Test case 2: Invalid URL format
    try:
        response = requests.get("not-a-url")
        results.append({"test": "invalid-url-format", "status": "unexpected_success"})
    except Exception as e:
        results.append(
            {
                "test": "invalid-url-format",
                "status": "expected_error",
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )

    return {"demo": "error-demo", "test_results": results}


@app.route("/features-demo")
def features_demo():
    """Demo various requests library features."""
    try:
        # Test with query parameters
        response = requests.get(
            "https://httpbin.org/get",
            params={"demo": "fastly-compute", "feature": "params"},
        )

        # Test response properties
        features = {
            "status_code": response.status_code,
            "ok": response.ok,
            "url": response.url,
            "headers_count": len(response.headers),
            "content_length": len(response.content),
            "text_length": len(response.text),
            "encoding": response.encoding,
            "content_type": response.headers.get("content-type", "unknown"),
        }

        return {"demo": "features-demo", "success": True, "features": features}

    except Exception as e:
        return {
            "demo": "features-demo",
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


# Create the HTTP handler
HttpIncoming = WsgiHttpIncoming(app)
