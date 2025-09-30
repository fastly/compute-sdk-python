use crate::bindings::wasi::sockets::instance_network::{self};
use crate::bindings::wasi::sockets::network::{self, GuestNetwork, Network};
use crate::{BOGUS_HANDLE, Wasiless};

impl GuestNetwork for Network {}

impl network::Guest for Wasiless {
    type Network = Network;
}

impl instance_network::Guest for Wasiless {
    fn instance_network() -> Network {
        unsafe { Network::from_handle(BOGUS_HANDLE) }
    }
}
