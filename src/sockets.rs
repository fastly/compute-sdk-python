use crate::Wasiless;
use crate::bindings::wasi::io::poll::Pollable;
use crate::bindings::wasi::sockets::instance_network;
use crate::bindings::wasi::sockets::ip_name_lookup;
use crate::bindings::wasi::sockets::network::{
    self, ErrorCode, GuestNetwork, IpAddressFamily, IpSocketAddress, Network, NetworkBorrow,
};
use crate::bindings::wasi::sockets::tcp::{self, GuestTcpSocket, TcpSocket};
use crate::bindings::wasi::sockets::tcp_create_socket;
use crate::bindings::wasi::sockets::udp::{
    self, GuestIncomingDatagramStream, GuestOutgoingDatagramStream, GuestUdpSocket,
    IncomingDatagram, IncomingDatagramStream, OutgoingDatagram, OutgoingDatagramStream, UdpSocket,
};
use crate::bindings::wasi::sockets::udp_create_socket;

impl GuestNetwork for Network {}

impl network::Guest for Wasiless {
    type Network = Network;
}

impl instance_network::Guest for Wasiless {
    fn instance_network() -> Network {
        unreachable!()
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

impl udp_create_socket::Guest for Wasiless {
    fn create_udp_socket(_address_family: IpAddressFamily) -> Result<UdpSocket, ErrorCode> {
        unimplemented!()
    }
}

impl GuestTcpSocket for TcpSocket {
    fn start_bind(
        &self,
        _network: tcp::NetworkBorrow<'_>,
        _local_address: tcp::IpSocketAddress,
    ) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn finish_bind(&self) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn start_connect(
        &self,
        _network: tcp::NetworkBorrow<'_>,
        _remote_address: tcp::IpSocketAddress,
    ) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn finish_connect(&self) -> Result<(tcp::InputStream, tcp::OutputStream), tcp::ErrorCode> {
        unreachable!()
    }

    fn start_listen(&self) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn finish_listen(&self) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn accept(
        &self,
    ) -> Result<(tcp::TcpSocket, tcp::InputStream, tcp::OutputStream), tcp::ErrorCode> {
        unreachable!()
    }

    fn local_address(&self) -> Result<tcp::IpSocketAddress, tcp::ErrorCode> {
        unreachable!()
    }

    fn remote_address(&self) -> Result<tcp::IpSocketAddress, tcp::ErrorCode> {
        unreachable!()
    }

    fn is_listening(&self) -> bool {
        unreachable!()
    }

    fn address_family(&self) -> tcp::IpAddressFamily {
        unreachable!()
    }

    fn set_listen_backlog_size(&self, _value: u64) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn keep_alive_enabled(&self) -> Result<bool, tcp::ErrorCode> {
        unreachable!()
    }

    fn set_keep_alive_enabled(&self, _value: bool) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn keep_alive_idle_time(&self) -> Result<tcp::Duration, tcp::ErrorCode> {
        unreachable!()
    }

    fn set_keep_alive_idle_time(&self, _value: tcp::Duration) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn keep_alive_interval(&self) -> Result<tcp::Duration, tcp::ErrorCode> {
        unreachable!()
    }

    fn set_keep_alive_interval(&self, _value: tcp::Duration) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn keep_alive_count(&self) -> Result<u32, tcp::ErrorCode> {
        unreachable!()
    }

    fn set_keep_alive_count(&self, _value: u32) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn hop_limit(&self) -> Result<u8, tcp::ErrorCode> {
        unreachable!()
    }

    fn set_hop_limit(&self, _value: u8) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn receive_buffer_size(&self) -> Result<u64, tcp::ErrorCode> {
        unreachable!()
    }

    fn set_receive_buffer_size(&self, _value: u64) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn send_buffer_size(&self) -> Result<u64, tcp::ErrorCode> {
        unreachable!()
    }

    fn set_send_buffer_size(&self, _value: u64) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }

    fn subscribe(&self) -> tcp::Pollable {
        unreachable!()
    }

    fn shutdown(&self, _shutdown_type: tcp::ShutdownType) -> Result<(), tcp::ErrorCode> {
        unreachable!()
    }
}

impl tcp::Guest for Wasiless {
    type TcpSocket = TcpSocket;
}

impl tcp_create_socket::Guest for Wasiless {
    fn create_tcp_socket(
        _address_family: tcp_create_socket::IpAddressFamily,
    ) -> Result<tcp_create_socket::TcpSocket, tcp_create_socket::ErrorCode> {
        unreachable!()
    }
}

impl ip_name_lookup::GuestResolveAddressStream for Wasiless {
    #[allow(unused_variables)]
    fn resolve_next_address(
        &self,
    ) -> Result<Option<ip_name_lookup::IpAddress>, ip_name_lookup::ErrorCode> {
        unreachable!()
    }
    #[allow(unused_variables)]
    fn subscribe(&self) -> ip_name_lookup::Pollable {
        unreachable!()
    }
}
impl ip_name_lookup::Guest for Wasiless {
    type ResolveAddressStream = Wasiless;
    #[allow(unused_variables)]
    fn resolve_addresses(
        network: ip_name_lookup::NetworkBorrow<'_>,
        name: String,
    ) -> Result<ip_name_lookup::ResolveAddressStream, ip_name_lookup::ErrorCode> {
        unreachable!()
    }
}
