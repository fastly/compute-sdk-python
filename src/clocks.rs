use crate::Wasiless;
use crate::bindings::wasi::clocks::monotonic_clock::{self, Duration, Instant};
use crate::bindings::wasi::clocks::wall_clock::{self, Datetime};
use crate::bindings::wasi::io::poll::Pollable;

impl wall_clock::Guest for Wasiless {
    fn now() -> Datetime {
        Datetime {
            seconds: 0,
            nanoseconds: 0,
        }
    }

    fn resolution() -> Datetime {
        Datetime {
            seconds: 0,
            nanoseconds: 0,
        }
    }
}

impl monotonic_clock::Guest for Wasiless {
    fn now() -> Instant {
        0
    }

    fn resolution() -> Duration {
        1 // A little less absurd than 0
    }

    fn subscribe_instant(_when: Instant) -> Pollable {
        unreachable!()
    }

    fn subscribe_duration(_when: Duration) -> Pollable {
        unreachable!()
    }
}
