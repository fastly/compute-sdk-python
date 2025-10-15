use crate::Wasiless;
use crate::bindings::exports::wasi::filesystem::{
    self,
    types::{
        Advice, Descriptor, DescriptorBorrow, DescriptorFlags, DescriptorStat, DescriptorType,
        DirectoryEntry, DirectoryEntryStream, Error, ErrorCode, Filesize, GuestDescriptor,
        GuestDirectoryEntryStream, MetadataHashValue, NewTimestamp, OpenFlags, PathFlags,
    },
};
use crate::bindings::wasi::io::streams::{InputStream, OutputStream};

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
    fn filesystem_error_code(_err: &Error) -> Option<ErrorCode> {
        None
    }
}

impl filesystem::preopens::Guest for Wasiless {
    fn get_directories() -> Vec<(Descriptor, String)> {
        Vec::new()
    }
}
