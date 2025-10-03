use crate::Wasiless;
use crate::bindings::wasi::random;

impl random::insecure::Guest for Wasiless {
    #[allow(unused_variables)]
    fn get_insecure_random_bytes(len: u64) -> Vec<u8> {
        unreachable!()
    }
    #[allow(unused_variables)]
    fn get_insecure_random_u64() -> u64 {
        unreachable!()
    }
}

impl random::insecure_seed::Guest for Wasiless {
    #[allow(unused_variables)]
    fn insecure_seed() -> (u64, u64) {
        unreachable!()
    }
}

impl random::random::Guest for Wasiless {
    #[allow(unused_variables)]
    fn get_random_bytes(len: u64) -> Vec<u8> {
        // TODO: This isn't random at all, let alone cryptographically so. As
        // such, it violates the WASI spec, which stipulates this must be left
        // out if it can't be random.
        Vec::with_capacity(len as usize)
    }
    #[allow(unused_variables)]
    fn get_random_u64() -> u64 {
        unreachable!()
    }
}
