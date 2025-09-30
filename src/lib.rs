// General philosophy thus far: Avoid returning error conditions; appear to
// succeed. But lie as little as possible beyond that: IO read and write
// routines claim 0 bytes were written, "successfully". This is in service of
// creating as little surprise for the caller as possible. Keep in mind this
// philosophy may be proven unhelpful through actual experience with the
// behavior of real-world clients. It may be helpful (and even less surprising)
// to crash as early as possible.

mod bindings;
mod cli;
mod clocks;
mod filesystem;
mod io;
mod sockets;

use bindings::export;

static mut BOGUS_RESOURCE: u8 = 0;
static BOGUS_HANDLE: u32 = 0;

/// Wasm component implementing WASI with as little functionality as possible
/// without trapping
struct Wasiless;

export!(Wasiless with_types_in bindings);
