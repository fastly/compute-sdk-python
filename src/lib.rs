// General philosophy thus far: Avoid returning error conditions; appear to
// succeed. But lie as little as possible beyond that: IO read and write
// routines claim 0 bytes were written, "successfully". This is in service of
// creating as little surprise for the caller as possible. Keep in mind this
// philosophy may be proven unhelpful through actual experience with the
// behavior of real-world clients. It may be helpful (and even less surprising)
// to crash as early as possible.

wit_bindgen::generate!({
    world: "wasiless",
    path: "wit",
    generate_all,
});

// This already miraculously exports wasi::cli::terminal_input::TerminalInput!

use exports::wasi::cli::terminal_input::{self, GuestTerminalInput, TerminalInput};
use exports::wasi::cli::terminal_output::{self, GuestTerminalOutput, TerminalOutput};
use exports::wasi::cli::terminal_stderr;
use exports::wasi::cli::terminal_stdin;
use exports::wasi::cli::terminal_stdout;
use exports::wasi::clocks::monotonic_clock::{self, Duration, Instant};
use exports::wasi::clocks::wall_clock::{self, Datetime};
use exports::wasi::filesystem::{
    self,
    types::{
        Advice, Descriptor, DescriptorBorrow, DescriptorFlags, DescriptorStat, DescriptorType,
        DirectoryEntry, DirectoryEntryStream, ErrorBorrow, ErrorCode, Filesize, GuestDescriptor,
        GuestDirectoryEntryStream, MetadataHashValue, NewTimestamp, OpenFlags, PathFlags,
    },
};
use exports::wasi::io::error::{self, Error, GuestError};
use exports::wasi::io::poll::{self, GuestPollable, Pollable, PollableBorrow};
use exports::wasi::io::streams::{
    self, GuestInputStream, GuestOutputStream, InputStream, InputStreamBorrow, OutputStream,
    StreamError,
};

static mut BOGUS_RESOURCE: u8 = 0;
static BOGUS_HANDLE: u32 = 0;

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

/// Wasm component implementing WASI with as little functionality as possible
/// without trapping
struct Wasiless;

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
        unsafe { Pollable::from_handle(BOGUS_HANDLE) }
    }

    fn subscribe_duration(_when: Duration) -> Pollable {
        unsafe { Pollable::from_handle(BOGUS_HANDLE) }
    }
}

impl GuestDescriptor for Descriptor {
    fn read_via_stream(&self, _offset: Filesize) -> Result<InputStream, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn write_via_stream(&self, _offset: Filesize) -> Result<OutputStream, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn append_via_stream(&self) -> Result<OutputStream, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn advise(
        &self,
        _offset: Filesize,
        _length: Filesize,
        _advice: Advice,
    ) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn sync_data(&self) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn get_flags(&self) -> Result<DescriptorFlags, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn get_type(&self) -> Result<DescriptorType, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn set_size(&self, _size: Filesize) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn set_times(
        &self,
        _data_access_timestamp: NewTimestamp,
        _data_modification_timestamp: NewTimestamp,
    ) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn read(&self, _length: Filesize, _offset: Filesize) -> Result<(Vec<u8>, bool), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn write(&self, _buffer: Vec<u8>, _offset: Filesize) -> Result<Filesize, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn read_directory(&self) -> Result<DirectoryEntryStream, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn sync(&self) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn create_directory_at(&self, _path: String) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn stat(&self) -> Result<DescriptorStat, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn stat_at(&self, _path_flags: PathFlags, _path: String) -> Result<DescriptorStat, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn set_times_at(
        &self,
        _path_flags: PathFlags,
        _path: String,
        _data_access_timestamp: NewTimestamp,
        _data_modification_timestamp: NewTimestamp,
    ) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn link_at(
        &self,
        _old_path_flags: PathFlags,
        _old_path: String,
        _new_descriptor: DescriptorBorrow<'_>,
        _new_path: String,
    ) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn open_at(
        &self,
        _path_flags: PathFlags,
        _path: String,
        _open_flags: OpenFlags,
        _flags: DescriptorFlags,
    ) -> Result<Descriptor, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn readlink_at(&self, _path: String) -> Result<String, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn remove_directory_at(&self, _path: String) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn rename_at(
        &self,
        _old_path: String,
        _new_descriptor: DescriptorBorrow<'_>,
        _new_path: String,
    ) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn symlink_at(&self, _old_path: String, _new_path: String) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn unlink_file_at(&self, _path: String) -> Result<(), ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn is_same_object(&self, _other: DescriptorBorrow<'_>) -> bool {
        false // arbitrary
    }

    fn metadata_hash(&self) -> Result<MetadataHashValue, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }

    fn metadata_hash_at(
        &self,
        _path_flags: PathFlags,
        _path: String,
    ) -> Result<MetadataHashValue, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }
}

impl GuestDirectoryEntryStream for DirectoryEntryStream {
    fn read_directory_entry(&self) -> Result<Option<DirectoryEntry>, ErrorCode> {
        Err(ErrorCode::Unsupported)
    }
}

impl filesystem::types::Guest for Wasiless {
    type Descriptor = Descriptor;
    type DirectoryEntryStream = DirectoryEntryStream;
    fn filesystem_error_code(_err: ErrorBorrow) -> Option<ErrorCode> {
        None
    }
}

export!(Wasiless);
