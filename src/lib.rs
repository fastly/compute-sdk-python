wit_bindgen::generate!({
    world: "python-virt",
    path: "wit",
    generate_all,
});

// This already miraculously exports wasi::cli::terminal_input::TerminalInput!

use exports::wasi::cli::terminal_input;
use exports::wasi::cli::terminal_input::{GuestTerminalInput, TerminalInput};

static mut ONE_TRUE_TERMINAL: u8 = 0;

// TODO: Make less bogus so it stands a chance of not crashing at runtime. For now, I'm just seeing if I can get it to link.
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

struct MyComponent;

impl terminal_input::Guest for MyComponent {
    type TerminalInput = TerminalInput;
}

export!(MyComponent);
