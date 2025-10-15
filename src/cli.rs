use crate::Wasiless;
use crate::bindings::exports::wasi::cli::terminal_input::{
    self, GuestTerminalInput, TerminalInput,
};
use crate::bindings::exports::wasi::cli::terminal_output::{
    self, GuestTerminalOutput, TerminalOutput,
};
use crate::bindings::exports::wasi::cli::{terminal_stderr, terminal_stdin, terminal_stdout};

impl GuestTerminalInput for TerminalInput {}

impl terminal_input::Guest for Wasiless {
    type TerminalInput = TerminalInput;
}

impl GuestTerminalOutput for TerminalOutput {}

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
