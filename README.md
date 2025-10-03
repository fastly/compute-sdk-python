# wasiless

Wasiless is a component that provides minimal or trapping implementations of all WASI interfaces, meant to allow the porting of dynamic runtimes like CPython which expect a normal OS with normal affordances like filesystems and sockets. Build CPython (or what have you) as a component, satisfy its imports with wasiless, then you can run it on a Compute worker.

Many of these stubs panic immediately, which is a nonissue if they are never actually called. This may be the overwhelmingly common case. In cases where it is not, we should instead return error codes like E_NOTSUP, which will allowed more graceful recovery or error reporting by the guest language (e.g. Python tracebacks).
