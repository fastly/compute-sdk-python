# Fastly Compute Python SDK

Experimental Python SDK for [Fastly Compute](https://www.fastly.com/products/edge-compute) services

## Highlights

- **Support for WSGI Frameworks**. Flask and Bottle examples are included for reference.
- Access from Python to **Fastly's API**
- Full **type hints** and IDE support

## Quick Start

Here's how to write your own Python WSGI app and run it on Fastly's edge network:

1. Install the package that provides the Fastly Python build tool and gives you access to the Fastly API:

   `pip install fastly-compute`
2. Make a project shaped like [our Flask example](/examples/flask-app). You may find it easiest to clone the [repository](/), copy the `examples/flask-app` folder, and modify it. If you change the name of the top-level `.py` file, be sure to also update the entrypoint (`entry = "your_top_level_module_name"`) in `pyproject.toml`.
3. `cd your-project`
4. Install the [Fastly CLI](https://www.fastly.com/documentation/reference/tools/cli/) if you don't already have it.
5. `fastly compute init`
6. Say yes when warned "The current directory isn't empty." Answer "[4] Other" when it asks for Language.
7. Add this to the bottom of `fastly.toml`:
   ```
   [scripts]
   build = "fastly-compute-py build"
   ```

8. `fastly compute build`
9. `fastly compute deploy`

## Run Some Examples on Your Own Machine

We ship [a few simple examples](examples/README.md) you can run locally to get a taste of what's possible.

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

See [CONTRIBUTING.md](CONTRIBUTING.md).
