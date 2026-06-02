# Fastly Compute Python SDK

Experimental Python SDK for [Fastly Compute](https://www.fastly.com/products/edge-compute) services.

## Highlights

- **Support for WSGI Frameworks**. Flask and Bottle examples are included for reference.
- Access from Python to **Fastly's API**
- Full **type hints** and IDE support

## Quick Start

### Install Dependencies

To work with `fastly-compute` in Python, you must install two system dependencies:

1. The [Fastly CLI](https://www.fastly.com/documentation/reference/tools/cli/).
2. The [uv](https://docs.astral.sh/uv/getting-started/installation/) Python package manager.

Additional dependencies, including the Python SDK for compute and build tooling, will be installed and managed by `uv` in an isolated environment.

### Set Up Your Project

For this basic project, we'll use the Flask microframework. We will create our project and add the SDK and build tooling by adding `fastly-compute` and `flask`:

   ```console
   $ uv init my-compute-service
   ...
   $ cd my-compute-service
   $ uv add fastly-compute flask
   ...
   ```

### Write Your Service

`uv init` automatically creates a `main.py` file in your project directory. Replace its contents with the following Flask application code:

```python
import platform
from flask import Flask
from fastly_compute.wsgi import WsgiHttpIncoming

app = Flask(__name__)


@app.route("/")
def index():
    version = platform.python_version()
    return f"Hello from Python {version} on Fastly Compute!"

HttpIncoming = WsgiHttpIncoming(app)
```

### Configure Compute Service Entry Point

The `fastly-compute-py` build tool, provided as part of the `fastly-compute` package, needs to be told about the module containing the compute service we just created. We can do this by modifying the `pyproject.toml` as follows:

```toml
# Add to end of pyproject.toml
[tool.fastly-compute]
entry = "main"
```

Then, let's do a quick test to make sure we are able to build a WebAssembly (Wasm) component:

```console
$ uv run fastly-compute-py build
Building Python application for Fastly Compute...
  Entry point: main
  Output: bin/main.wasm
  Resolving Python dependencies...
  Componentizing Python application...
  Composing final WebAssembly module...
  Injecting Fastly metadata...
✓ Build complete: bin/main.wasm
```

### Test and Deploy Your Service Using the Fastly CLI

Now that we have the skeleton of our service, let's test it using the [Fastly CLI](https://www.fastly.com/documentation/reference/tools/cli/).

1. Run `fastly compute init`
2. Say yes when warned "The current directory isn't empty." Answer "Other" when it asks for Language.
3. Add this to the bottom of `fastly.toml`:

   ```toml
   [scripts]
   build = "uv run fastly-compute-py build"
   ```

With that in place, we can now run `fastly compute serve` to test our service locally. When you're ready, you can use the Fastly CLI to deploy the service to the production fleet and perform other actions.

See the [`examples/`](https://github.com/fastly/compute-sdk-python/examples/) directory for more examples.

## Run Some Examples on Your Own Machine

We ship [a few simple examples](https://github.com/fastly/compute-sdk-python/blob/main/examples/README.md) you can run locally to get a taste of what's possible.

## Status

Currently supports...
- Building pure Python into WebAssembly components
- Creating Python bindings from Fastly's WIT files
- Hosting web frameworks by adapting Fastly's API to WSGI
- Hosting non-WSGI applications by writing directly against Fastly's API

## Caveats

- So our memory-snapshotting build process can retain them, all the packages
  needed at runtime must get imported when your entrypoint (e.g. `flask-app.py`)
  is imported. This can happen transitively. But beware of deferred imports like
  non-top-level ones; if they aren't triggered by importing your entrypoint,
  they will fail at runtime. (If you have third-party code that uses
  non-top-level imports, you can ensure they work by importing them at the top
  level in your own code.)
- Third-party C extension modules are not yet supported.
- Our in-Python API may change backward-incompatibly during this beta period.

## Contributing

See [CONTRIBUTING.md](https://github.com/fastly/compute-sdk-python/blob/main/CONTRIBUTING.md).
