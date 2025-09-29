wit_bindgen::generate!({
    world: "wasiless",
    path: "wit",
    generate_all,
});

// This already miraculously exports wasi::cli::terminal_input::TerminalInput!

use exports::wasi::cli::terminal_input::{self, GuestTerminalInput, TerminalInput};
use exports::wasi::cli::terminal_output::{self, GuestTerminalOutput, TerminalOutput};
use exports::wasi::cli::terminal_stderr;
use exports::wasi::cli::terminal_stdin;
use exports::wasi::cli::terminal_stdout;
use exports::wasi::io::error::{self, Error, GuestError};
use exports::wasi::io::poll::{self, GuestPollable, Pollable, PollableBorrow};

static mut BOGUS_RESOURCE: u8 = 0;

// TODO: Make less bogus so it stands a chance of not crashing at runtime. For
// now, I'm just seeing if I can get it to link.
impl GuestTerminalInput for TerminalInput {
    unsafe fn _resource_new(_val: *mut u8) -> u32
    where
        Self: Sized,
    {
        0
    }

    fn _resource_rep(_handle: u32) -> *mut u8
    where
        Self: Sized,
    {
        &raw mut BOGUS_RESOURCE
    }
}

/// Wasm component implementing WASI with as little functionality as possible
/// without trapping
struct Wasiless;

impl terminal_input::Guest for Wasiless {
    type TerminalInput = TerminalInput;
}

// TODO: Make less bogus, as above. Make all BOGUS_RESOURCE users less bogus.
impl GuestTerminalOutput for TerminalOutput {
    unsafe fn _resource_new(_val: *mut u8) -> u32
    where
        Self: Sized,
    {
        0
    }

    fn _resource_rep(_handle: u32) -> *mut u8
    where
        Self: Sized,
    {
        &raw mut BOGUS_RESOURCE
    }
}

impl terminal_output::Guest for Wasiless {
    type TerminalOutput = TerminalOutput;
}

impl terminal_stdin::Guest for Wasiless {
    fn get_terminal_stdin() -> Option<<Wasiless as terminal_input::Guest>::TerminalInput> {
        None
    }
}

impl terminal_stdout::Guest for Wasiless {
    fn get_terminal_stdout() -> Option<<Wasiless as terminal_output::Guest>::TerminalOutput> {
        None
    }
}

impl terminal_stderr::Guest for Wasiless {
    fn get_terminal_stderr() -> Option<<Wasiless as terminal_output::Guest>::TerminalOutput> {
        None
    }
}

impl GuestError for Error {
    unsafe fn _resource_new(_val: *mut u8) -> u32
    where
        Self: Sized,
    {
        0
    }

    fn _resource_rep(_handle: u32) -> *mut u8
    where
        Self: Sized,
    {
        &raw mut BOGUS_RESOURCE
    }

    fn to_debug_string(&self) -> String {
        "".to_owned()
    }
}

impl error::Guest for Wasiless {
    type Error = Error;
}

impl GuestPollable for Pollable {
    unsafe fn _resource_new(_val: *mut u8) -> u32
    where
        Self: Sized,
    {
        0
    }

    fn _resource_rep(_handle: u32) -> *mut u8
    where
        Self: Sized,
    {
        &raw mut BOGUS_RESOURCE
    }

    /// Returns true for consistency with the fact that our block() doesn't block.
    fn ready(&self) -> bool {
        true
    }

    /// Never blocks, lest we block forever.
    fn block(&self) -> () {
        ()
    }
}

impl poll::Guest for Wasiless {
    type Pollable = Pollable;

    /// This is a real implementation, in an attempt to present a consistent
    /// picture of our fake reality to callers and thus avoid provoking crashes
    /// unnecessarily.
    fn poll(pollables: Vec<PollableBorrow>) -> Vec<u32> {
        if pollables.len() > (u32::MAX as usize) {
            panic!("list of pollables too long to be indexed with a u32")
        }
        pollables
            .iter()
            .enumerate()
            .filter_map(|(i, p)| {
                if p.get::<self::Pollable>().ready() {
                    Some(i as u32)
                } else {
                    None
                }
            })
            .collect()
    }
}

export!(Wasiless);
