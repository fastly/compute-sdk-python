use crate::Wasiless;
use crate::bindings::wasi::sockets::network::{self, GuestNetwork, Network};

impl GuestNetwork for Network {}

impl network::Guest for Wasiless {
    type Network = Network;
}
