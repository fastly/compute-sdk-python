# wasiless

Wasiless is a WebAssembly component that provides minimal or trapping implementations of all WASI interfaces, meant to allow the porting of dynamic runtimes like CPython which expect a normal OS, with normal affordances like filesystems and sockets. Build CPython (or some other runtime) as a component, satisfy its imports with wasiless, and you should be able to run it in an environment that provides only a subset of WASI, like [Viceroy](https://github.com/fastly/Viceroy).

Here is an example composition of wasiless and a Python component (built using componentize-py) for use with Viceroy:

```
package fastly:python-wasiless;

// Instantiate wasiless, minimal or crashing implementations of irrelevant WASI interfaces:
let wasiless = new fastly:wasiless {
    ...
};

// Instantiate the Python component. Pass in the 0.2.6 routines from wasiless,
// even when Python wants a different version:
let app = new app:component {
  "wasi:cli/terminal-input@0.2.0": wasiless["wasi:cli/terminal-input@0.2.6"],
  "wasi:cli/terminal-output@0.2.0": wasiless["wasi:cli/terminal-output@0.2.6"],
  "wasi:cli/terminal-stdin@0.2.0": wasiless["wasi:cli/terminal-stdin@0.2.6"],
  "wasi:cli/terminal-stdout@0.2.0": wasiless["wasi:cli/terminal-stdout@0.2.6"],
  "wasi:cli/terminal-stderr@0.2.0": wasiless["wasi:cli/terminal-stderr@0.2.6"],
  "wasi:filesystem/types@0.2.0": wasiless["wasi:filesystem/types@0.2.6"],
  "wasi:filesystem/preopens@0.2.0": wasiless["wasi:filesystem/preopens@0.2.6"],
  "wasi:sockets/network@0.2.0": wasiless["wasi:sockets/network@0.2.6"],
  "wasi:sockets/instance-network@0.2.0": wasiless["wasi:sockets/instance-network@0.2.6"],
  "wasi:sockets/udp@0.2.0": wasiless["wasi:sockets/udp@0.2.6"],
  "wasi:sockets/udp-create-socket@0.2.0": wasiless["wasi:sockets/udp-create-socket@0.2.6"],
  "wasi:sockets/tcp@0.2.0": wasiless["wasi:sockets/tcp@0.2.6"],
  "wasi:sockets/tcp-create-socket@0.2.0": wasiless["wasi:sockets/tcp-create-socket@0.2.6"],
  "wasi:sockets/ip-name-lookup@0.2.0": wasiless["wasi:sockets/ip-name-lookup@0.2.6"],
  "wasi:random/insecure@0.2.0": wasiless["wasi:random/insecure@0.2.6"],
  "wasi:random/insecure-seed@0.2.0": wasiless["wasi:random/insecure-seed@0.2.6"],
  ...
};

export app.exports;
export app["fastly:compute/http-incoming"];
```

Build wasiless as a p2 component as follows:

``` shell
cargo build --release --target wasm32-wasip2
```

To apply this, save it as `wrap_app_in_wasiless.wac`, then invoke wac like...

```
wac compose --dep fastly:wasiless=wasiless.wasm --dep app:component=python_app.wasm -o composed.wasm wrap_app_in_wasiless.wac
```

## Caveats and philosophy

Many of wasiless’ functions panic immediately. This is a nonissue if they are never actually called, which appears to be the common case. Where this is not true, we strive instead to return error codes like `ENOTSUP`, which allows more graceful recovery or error reporting by the guest language (e.g. Python tracebacks).
