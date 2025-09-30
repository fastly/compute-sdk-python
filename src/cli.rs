use crate::bindings::wasi::cli::terminal_input::{self, GuestTerminalInput, TerminalInput};
use crate::bindings::wasi::cli::terminal_output::{self, GuestTerminalOutput, TerminalOutput};
use crate::bindings::wasi::cli::terminal_stderr;
use crate::bindings::wasi::cli::terminal_stdin;
use crate::bindings::wasi::cli::terminal_stdout;
use crate::{BOGUS_HANDLE, BOGUS_RESOURCE, Wasiless};

// TODO: Make less bogus so it stands a chance of not crashing at runtime. Same
// for other BOGUS_RESOURCE and BOGUS_HANDLE users. For now, I'm just seeing if
// I can get it to link.
impl GuestTerminalInput for TerminalInput {
    unsafe fn _resource_new(_val: *mut u8) -> u32
    where
        Self: Sized,
    {
        BOGUS_HANDLE
    }

    fn _resource_rep(_handle: u32) -> *mut u8
    where
        Self: Sized,
    {
        &raw mut BOGUS_RESOURCE
    }
}

impl terminal_input::Guest for Wasiless {
    type TerminalInput = TerminalInput;
}

impl GuestTerminalOutput for TerminalOutput {
    unsafe fn _resource_new(_val: *mut u8) -> u32
    where
        Self: Sized,
    {
        BOGUS_HANDLE
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
