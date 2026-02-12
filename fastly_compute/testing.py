"""Testing utilities for Fastly Compute tests.

This module provides pytest fixtures and base classes for testing
Fastly Compute services with viceroy.

To enable automatic viceroy output on test failures, add this to your conftest.py:

    pytest_plugins = ["fastly_compute.pytest_plugin"]
"""

import os
import pickle
import socket
import subprocess
import sys
import threading
import time
from base64 import a85decode
from contextlib import chdir, contextmanager
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp
from types import MethodType
from urllib.parse import quote

import pytest
import requests
import tomli_w


@dataclass
class ViceroyServer:
    """Represents a running viceroy server instance."""

    process: subprocess.Popen
    base_url: str
    output_lines: list[str]  # Capture output for debugging


class ViceroyTestBase:
    """Base class for viceroy tests.

    Provides common functionality for testing Fastly Compute services.
    Inherit from this class and use the viceroy_server fixture.

    Note: This assumes your WASM file is already built. Use your build system
    (e.g., Makefile) to ensure the WASM file is up to date before running tests.

    Example:
        ```python
        import pytest
        from fastly_compute.testing import ViceroyTestBase

        class TestMyService(ViceroyTestBase):
            def test_my_endpoint(self):
                response = self.get("/my-endpoint")
                assert response.status_code == 200
        ```
    """

    REQUEST_TIMEOUT = 10
    WASM_FILE = "build/bottle-app.composed.wasm"  # Default to the main example
    _server: ViceroyServer | None = None  # Will be set by the fixture

    @classmethod
    def server(cls) -> ViceroyServer:
        """Access server properties."""
        assert cls._server is not None
        return cls._server

    # Configuration for backend testing
    VICEROY_CONFIG = None  # Dict with viceroy config, or None for no config
    _config_file_path = None  # Will store temp config file path

    @staticmethod
    def _find_free_port() -> int:
        """Find an available port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            port = s.getsockname()[1]
        return port

    @classmethod
    def _create_viceroy_config(cls, backends: dict[str, str] | None = None) -> str:
        """Create a temporary viceroy configuration file.

        Args:
            backends: Dict mapping backend names to URLs
                     e.g., {"httpbin": "http://127.0.0.1:8080"}

        Returns:
            Path to the temporary configuration file
        """
        config_dict = {}

        # Add backends if provided
        if backends:
            config_dict["local_server"] = {
                "backends": {name: {"url": url} for name, url in backends.items()}
            }

        # Add any additional config from class
        if cls.VICEROY_CONFIG:
            # Merge with class config
            if "local_server" in config_dict and "local_server" in cls.VICEROY_CONFIG:
                # Merge local_server sections
                for key, value in cls.VICEROY_CONFIG["local_server"].items():
                    if key == "backends" and "backends" in config_dict["local_server"]:
                        # Merge backends
                        config_dict["local_server"]["backends"].update(value)
                    else:
                        config_dict["local_server"][key] = value
            else:
                # Add other sections
                config_dict.update(cls.VICEROY_CONFIG)

        # Generate TOML content
        toml_content = tomli_w.dumps(config_dict)

        # Create temporary file
        with NamedTemporaryFile(
            prefix="viceroy_config_", suffix=".toml", mode="w", delete=False
        ) as f:
            f.write(toml_content)
            return f.name

    @classmethod
    def set_up_backends(cls, backends: dict[str, str]):
        """Set up backends for testing.

        Call this in setUpClass or as a class-level setup.

        Args:
            backends: Dict mapping backend names to URLs
                     e.g., {"httpbin": "http://127.0.0.1:8080"}
        """
        cls._test_backends = backends

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def viceroy_server(cls):
        """Start viceroy server for the duration of the test class.

        Note: This assumes the WASM file already exists. Use your build system
        to ensure it's built before running tests.

        Returns:
            ViceroyServer: Server instance with process, base_url, and captured output
        """
        print("Starting viceroy server...")

        # Check if WASM file exists
        wasm_path = Path(cls.WASM_FILE)
        if not wasm_path.exists():
            pytest.fail(
                f"WASM file '{cls.WASM_FILE}' not found. Please build it first."
            )

        # Find an available port
        port = cls._find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        output_lines: list[str] = []  # Capture all output for debugging
        output_lock = threading.Lock()
        stop_capture = threading.Event()

        # Create config file if needed
        config_file_path = None
        if hasattr(cls, "_test_backends") or cls.VICEROY_CONFIG:
            # Get backends from test setup (if any)
            backends = getattr(cls, "_test_backends", None)
            config_file_path = cls._create_viceroy_config(backends)
            cls._config_file_path = config_file_path

        # Build viceroy command
        viceroy_cmd = [
            os.getenv("VICEROY", "viceroy"),
            "serve",
            cls.WASM_FILE,
            "--addr",
            f"127.0.0.1:{port}",
            "-v",
        ]
        if config_file_path:
            viceroy_cmd.extend(["-C", config_file_path])

        # Start viceroy process
        process = subprocess.Popen(
            viceroy_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Start background thread to continuously capture output
        def capture_output_thread():
            """Continuously capture viceroy output throughout test execution."""
            assert process.stdout is not None, "stdout should be PIPE"
            while not stop_capture.is_set():
                line = process.stdout.readline()
                if not line:  # EOF
                    break
                with output_lock:
                    output_lines.append(line.strip())

        output_thread = threading.Thread(target=capture_output_thread, daemon=True)
        output_thread.start()

        # Wait for server to be ready
        timeout = 15
        start_time = time.monotonic()
        server_ready = False

        while time.monotonic() - start_time < timeout:
            if process.poll() is not None:
                # Process died, collect output and fail
                stop_capture.set()
                time.sleep(0.1)  # Give thread time to capture final output
                with output_lock:
                    all_output = "\n".join(output_lines)
                pytest.fail(f"Viceroy failed to start. Output:\n{all_output}")

            # Check if we've seen the "Listening on" message
            with output_lock:
                for line in output_lines:
                    if "Listening on" in line:
                        print(f"Server ready: {line}")
                        server_ready = True
                        break

            if server_ready:
                break

        if not server_ready:
            stop_capture.set()
            process.terminate()
            process.wait()
            with output_lock:
                all_output = "\n".join(output_lines)
            pytest.fail(
                f"Viceroy server did not start within {timeout} seconds. Output:\n{all_output}"
            )

        server = ViceroyServer(
            process=process, base_url=base_url, output_lines=output_lines
        )

        # Set the server as a class attribute so methods can access it
        cls._server = server

        yield server

        # Cleanup: stop output capture and terminate the process
        print("Stopping viceroy server...")
        stop_capture.set()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        # Clean up config file if we created one
        if cls._config_file_path and os.path.exists(cls._config_file_path):
            try:
                os.unlink(cls._config_file_path)
            except OSError:
                pass  # Ignore cleanup errors
            cls._config_file_path = None

    @classmethod
    def get(cls, path: str, **kwargs) -> requests.Response:
        """Make a GET request to the viceroy server.

        Args:
            path: URL path to request
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            requests.Response: The HTTP response
        """
        return cls.request("GET", path, **kwargs)

    @classmethod
    def post(cls, path: str, **kwargs) -> requests.Response:
        """Make a POST request to the viceroy server.

        Args:
            path: URL path to request
            **kwargs: Additional arguments passed to requests.post()

        Returns:
            requests.Response: The HTTP response
        """
        return cls.request("POST", path, **kwargs)

    @classmethod
    def request(cls, method: str, path: str, **kwargs) -> requests.Response:
        """Make an HTTP request to the viceroy server.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: URL path to request
            **kwargs: Additional arguments passed to requests.request()

        Returns:
            requests.Response: The HTTP response
        """
        timeout = kwargs.pop("timeout", cls.REQUEST_TIMEOUT)
        response = requests.request(
            method, f"{cls.server().base_url}{path}", timeout=timeout, **kwargs
        )
        return response


@contextmanager
def _temp_directory():
    """Make a temporary directory, and delete it afterward."""
    dir = Path(mkdtemp())
    yield dir
    rmtree(dir)


class AutoViceroyTestBase(ViceroyTestBase):
    """Test base class which tests against an ephemeral, generated WASM application.

    Whereas :class:`ViceroyTestBase` works against an on-disk WASM file, this
    lets you put your WASM-side code next to your testrunner code through the
    use of the :func:`on_viceroy` decorator, factoring away the build process,
    the HTTP requests to Viceroy, and the serialization protocol used in those
    requests.
    """

    # Whether this process is running (as wasm) on Viceroy:
    _is_on_viceroy = False

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def ephemeral_wasm(cls):
        """Build an ad hoc WASM which performs the server-side half of the
        :method:`on_viceroy` magic.
        """
        # Import the module where the tests we'll be running are defined. Having
        # them imported in a statically analyzable way allows componentize-py to
        # walk them and include all transitive dependencies into the wasm.
        code = f'''"""Bottle app that serves as a remote runner for chunks of test code that need
to execute in Viceroy
"""

from base64 import a85encode
import pickle
from urllib.parse import unquote

import bottle
from bottle import Bottle

from fastly_compute.testing import AutoViceroyTestBase
AutoViceroyTestBase._is_on_viceroy = True

import {cls.__module__}
from fastly_compute.wsgi import WsgiHttpIncoming


bottle.debug(True)
app = Bottle()


@app.route("/<func_path>")
def run_viceroy_chunk(func_path: str) -> dict[str, str | bool]:
    """Run a method from a test class in Viceroy, and return its result over
    HTTP.

    The method must be a class method so we don't have to instantiate the class.
    (Once upon a time, we relaxed this by requiring the class to be instantiable
    with no args. We could do it again.)

    :arg func_path: Fully qualified name of the ``@in_viceroy``-decorated
        function to run, typically like "TestClass.test_method".
    """
    func_path = unquote(func_path)

    # Walk down the dotted path to get method to run:
    method = {cls.__module__}
    for part in func_path.split("."):
        class_ = method
        method = getattr(method, part)

    try:
        result = method(class_)
        is_exception = False
    except Exception as exc:
        result = exc
        is_exception = True

    return {{"result": a85encode(pickle.dumps(result)).decode("ascii"),
             "is_exception": is_exception}}


HttpIncoming = WsgiHttpIncoming(app)
'''
        with _temp_directory() as temp_dir:
            (temp_dir / "main.py").write_text(code)
            cls.WASM_FILE = str(temp_dir / "viceroy_test_code.wasm")
            try:
                with chdir(temp_dir):  # fastly-compute-py -e arg is unreliable.
                    # Import the native _fastly_compute_py locally so
                    # componentize-py can wrap this testing.py module for use
                    # under Viceroy, where non-WASI native modules don't work:
                    from fastly_compute.fastly_compute_py import (
                        run_main_py as fastly_compute_py,
                    )

                    # Rather than creating a new venv, we build within the one
                    # we're in right now. That is guaranteed to have the libs
                    # needed to load both the customer code (because the
                    # customer took responsibility for installing their deps)
                    # and fastly_compute (or we wouldn't be here).
                    fastly_compute_py(
                        [
                            "dummy",
                            "build",
                            "--output",
                            cls.WASM_FILE,
                            "--virtualenv",
                            sys.prefix,
                        ]
                    )
                yield
            finally:
                del cls.WASM_FILE


def _as_class_method(method) -> classmethod:
    """If a method is not already a class method, make it one."""
    return classmethod(method) if isinstance(method, MethodType) else method


def on_viceroy(method) -> classmethod:
    """Decorator for making a method run on the testrunner's Viceroy server

    Decorate a method with this, and it will automagically run under Viceroy
    when called. The method must be in a subclass of AutoViceroyTestBase.

    Notes and caveats:
    * Return values and raised exceptions must be pickleable.
    * If the decorated method is not already a class method, we make it one, in
      service to conciseness.
    """
    # TODO: Complain if the decorated method isn't in a subclass of AutoViceroyTestBase.

    # Advise users in the readme to put their tests within their package,
    # not outside it. They need to be importable, because the
    # test-code-runner template needs to be able to import them.
    if AutoViceroyTestBase._is_on_viceroy:
        return _as_class_method(method)
    else:
        # I'm on the host, in the testrunner.
        #
        # In the future, we could support incoming params.

        @wraps(method)
        def ask_viceroy_to_call_method(cls):
            """Make a request to Viceroy, passing along a path to a function to
            run within it.
            """
            response = cls.get("/" + quote(method.__qualname__))
            response.raise_for_status()
            data = response.json()
            # Unpickle response. Return retval or raise exception. (Yes, raise.
            # We want exceptions to not be forgotten by default.)
            result = pickle.loads(a85decode(data["result"]))
            if data["is_exception"]:
                raise result
            return result

        return _as_class_method(ask_viceroy_to_call_method)
