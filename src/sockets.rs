use crate::bindings::wasi::io::poll::Pollable;
use crate::bindings::wasi::sockets::instance_network;
use crate::bindings::wasi::sockets::network::{
    self, ErrorCode, GuestNetwork, IpAddressFamily, IpSocketAddress, Network, NetworkBorrow,
};
use crate::bindings::wasi::sockets::udp::{
    self, GuestIncomingDatagramStream, GuestOutgoingDatagramStream, GuestUdpSocket,
    IncomingDatagram, IncomingDatagramStream, OutgoingDatagram, OutgoingDatagramStream, UdpSocket,
};
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

impl GuestUdpSocket for UdpSocket {
    fn start_bind(
        &self,
        _network: NetworkBorrow,
        _local_address: IpSocketAddress,
    ) -> Result<(), ErrorCode> {
        unimplemented!()
    }

    fn finish_bind(&self) -> Result<(), ErrorCode> {
        unimplemented!()
    }

    fn stream(
        &self,
        _remote_address: Option<IpSocketAddress>,
    ) -> Result<(IncomingDatagramStream, OutgoingDatagramStream), ErrorCode> {
        unimplemented!()
    }

    fn local_address(&self) -> Result<IpSocketAddress, ErrorCode> {
        unreachable!()
    }

    fn remote_address(&self) -> Result<IpSocketAddress, ErrorCode> {
        unreachable!()
    }

    fn address_family(&self) -> IpAddressFamily {
        unreachable!()
    }

    fn unicast_hop_limit(&self) -> Result<u8, ErrorCode> {
        unreachable!()
    }

    fn set_unicast_hop_limit(&self, _value: u8) -> Result<(), ErrorCode> {
        unreachable!()
    }

    fn receive_buffer_size(&self) -> Result<u64, ErrorCode> {
        unreachable!()
    }

    fn set_receive_buffer_size(&self, _value: u64) -> Result<(), ErrorCode> {
        unreachable!()
    }

    fn send_buffer_size(&self) -> Result<u64, ErrorCode> {
        unreachable!()
    }

    fn set_send_buffer_size(&self, _value: u64) -> Result<(), ErrorCode> {
        unreachable!()
    }

    fn subscribe(&self) -> Pollable {
        unreachable!()
    }
}

impl GuestIncomingDatagramStream for IncomingDatagramStream {
    fn receive(&self, _max_results: u64) -> Result<Vec<IncomingDatagram>, ErrorCode> {
        unreachable!()
    }

    fn subscribe(&self) -> Pollable {
        unreachable!()
    }
}

impl GuestOutgoingDatagramStream for OutgoingDatagramStream {
    fn check_send(&self) -> Result<u64, ErrorCode> {
        unreachable!()
    }
    fn send(&self, _datagrams: Vec<OutgoingDatagram>) -> Result<u64, ErrorCode> {
        unreachable!()
    }
    fn subscribe(&self) -> Pollable {
        unreachable!()
    }
}

impl udp::Guest for Wasiless {
    type UdpSocket = UdpSocket;
    type IncomingDatagramStream = IncomingDatagramStream;
    type OutgoingDatagramStream = OutgoingDatagramStream;
}
