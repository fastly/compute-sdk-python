wit_bindgen::generate!({
    world: "wasiless",
    path: "wit",
    generate_all,
});

// This already miraculously exports wasi::cli::terminal_input::TerminalInput!

use exports::wasi::cli::terminal_input;
use exports::wasi::cli::terminal_input::{GuestTerminalInput, TerminalInput};
use exports::wasi::cli::terminal_output;
use exports::wasi::cli::terminal_output::{GuestTerminalOutput, TerminalOutput};
use exports::wasi::cli::terminal_stderr;
use exports::wasi::cli::terminal_stdin;
use exports::wasi::cli::terminal_stdout;

static mut ONE_TRUE_TERMINAL: u8 = 0;

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
        &raw mut ONE_TRUE_TERMINAL
    }
}

/// Wasm component implementing WASI with as little functionality as possible
/// without trapping
struct Wasiless;

impl terminal_input::Guest for Wasiless {
    type TerminalInput = TerminalInput;
}

// TODO: Make less bogus, as above.
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
        &raw mut ONE_TRUE_TERMINAL
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

export!(Wasiless);
