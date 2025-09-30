use crate::bindings::wasi::io::error::{self, Error, GuestError};
use crate::bindings::wasi::io::poll::Pollable;
use crate::bindings::wasi::io::poll::{self, GuestPollable, PollableBorrow};
use crate::bindings::wasi::io::streams::{
    self, GuestInputStream, GuestOutputStream, InputStream, InputStreamBorrow, OutputStream,
    StreamError,
};
use crate::{BOGUS_HANDLE, BOGUS_RESOURCE, Wasiless};

impl GuestError for Error {
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

    fn to_debug_string(&self) -> String {
        "".to_owned()
    }
}

impl error::Guest for Wasiless {
    type Error = Error;
}

impl GuestPollable for Pollable {
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

    /// Returns true for consistency with the fact that our block() doesn't block.
    fn ready(&self) -> bool {
        true
    }

    /// Never blocks, lest we block forever.
    fn block(&self) -> () {
        ()
    }
}

impl poll::Guest for Wasiless {
    type Pollable = Pollable;

    /// This is a real implementation, in an attempt to present a consistent
    /// picture of our fake reality to callers and thus avoid provoking crashes
    /// unnecessarily.
    fn poll(pollables: Vec<PollableBorrow>) -> Vec<u32> {
        if pollables.len() > (u32::MAX as usize) {
            panic!("list of pollables too long to be indexed with a u32")
        }
        pollables
            .iter()
            .enumerate()
            .filter_map(|(i, p)| {
                if p.get::<self::Pollable>().ready() {
                    Some(i as u32)
                } else {
                    None
                }
            })
            .collect()
    }
}

impl GuestInputStream for InputStream {
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

    fn read(&self, _len: u64) -> Result<Vec<u8>, StreamError> {
        Ok(Vec::new())
    }

    fn blocking_read(&self, _len: u64) -> Result<Vec<u8>, StreamError> {
        Ok(Vec::new())
    }

    fn skip(&self, _len: u64) -> Result<u64, StreamError> {
        Ok(0)
    }

    fn blocking_skip(&self, _len: u64) -> Result<u64, StreamError> {
        Ok(0)
    }

    fn subscribe(&self) -> Pollable {
        unsafe { Pollable::from_handle(BOGUS_HANDLE) }
    }
}

/// Writes appear to go through without error but also report back that they wrote 0 bytes.
impl GuestOutputStream for OutputStream {
    // TODO: Maybe we can delete all these _resource*() funcs; the trait has a crashing default impl.
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

    fn check_write(&self) -> Result<u64, StreamError> {
        Ok(4096) // TODO: Make this interlock with subscribe().
    }

    fn write(&self, _contents: Vec<u8>) -> Result<(), StreamError> {
        Ok(())
    }

    fn blocking_write_and_flush(&self, _contents: Vec<u8>) -> Result<(), StreamError> {
        Ok(())
    }

    fn flush(&self) -> Result<(), StreamError> {
        Ok(())
    }

    fn blocking_flush(&self) -> Result<(), StreamError> {
        Ok(())
    }

    fn subscribe(&self) -> Pollable {
        unsafe { Pollable::from_handle(BOGUS_HANDLE) }
    }

    fn write_zeroes(&self, _len: u64) -> Result<(), StreamError> {
        Ok(())
    }

    fn blocking_write_zeroes_and_flush(&self, _len: u64) -> Result<(), StreamError> {
        Ok(())
    }

    fn splice(&self, _src: InputStreamBorrow, _len: u64) -> Result<u64, StreamError> {
        Ok(0)
    }

    fn blocking_splice(&self, _src: InputStreamBorrow, _len: u64) -> Result<u64, StreamError> {
        Ok(0)
    }
}

impl streams::Guest for Wasiless {
    type InputStream = InputStream;
    type OutputStream = OutputStream;
}
