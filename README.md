# wasiless

Wasiless is a WebAssembly component that provides minimal or trapping implementations of all WASI interfaces, meant to allow the porting of dynamic runtimes like CPython which expect a normal OS, with normal affordances like filesystems and sockets. Build CPython (or some other runtime) as a component, satisfy its imports with wasiless, and you should be able to run it in an environment that provides only a subset of WASI, like [Viceroy](https://github.com/fastly/Viceroy).

## Build

Build wasiless as a WASIp2 component using `make`.

## Use

Here is an example composition of wasiless and a Python component (built using componentize-py) for use with Viceroy:

```
package fastly:python-wasiless;

// Instantiate wasiless to satisfy irrelevant WASI interfaces:
let wasiless = new fastly:wasiless { ... };

// Instantiate the Python component:
let app = new app:component { ...wasiless, ... };

// Export only the HTTP handler, not the extraneous `exports` bundle:
export app["fastly:compute/http-incoming"];
```

To apply this, save it as `wrap_app_in_wasiless.wac`, then invoke wac like...

```
wac compose --dep fastly:wasiless=wasiless.wasm --dep app:component=python_app.wasm -o composed.wasm wrap_app_in_wasiless.wac
```

## Caveats and philosophy

Many of wasiless’ functions panic immediately. This is a nonissue if they are never actually called, which appears to be the common case. Where this is not true, we strive instead to return error codes like `ENOTSUP`, which allows more graceful recovery or error reporting by the guest language (e.g. Python tracebacks).
