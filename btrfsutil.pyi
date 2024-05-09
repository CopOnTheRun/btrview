import types
from _typeshed import Incomplete
from typing import Any, ClassVar

ERROR_DEFAULT_SUBVOL_FAILED: int
ERROR_FS_INFO_FAILED: int
ERROR_GET_SUBVOL_INFO_FAILED: int
ERROR_GET_SUBVOL_ROOTREF_FAILED: int
ERROR_INO_LOOKUP_FAILED: int
ERROR_INO_LOOKUP_USER_FAILED: int
ERROR_INVALID_ARGUMENT: int
ERROR_NOT_BTRFS: int
ERROR_NOT_SUBVOLUME: int
ERROR_NO_MEMORY: int
ERROR_OPEN_FAILED: int
ERROR_RMDIR_FAILED: int
ERROR_SEARCH_FAILED: int
ERROR_SNAP_CREATE_FAILED: int
ERROR_SNAP_DESTROY_FAILED: int
ERROR_START_SYNC_FAILED: int
ERROR_STATFS_FAILED: int
ERROR_STAT_FAILED: int
ERROR_STOP_ITERATION: int
ERROR_SUBVOLUME_NOT_FOUND: int
ERROR_SUBVOL_CREATE_FAILED: int
ERROR_SUBVOL_GETFLAGS_FAILED: int
ERROR_SUBVOL_SETFLAGS_FAILED: int
ERROR_SYNC_FAILED: int
ERROR_UNLINK_FAILED: int
ERROR_WAIT_SYNC_FAILED: int

class BtrfsUtilError(OSError):
    btrfsutilerror: Incomplete
    @classmethod
    def __init__(cls, *args, **kwargs) -> None: ...

class QgroupInherit:
    def __init__(self) -> newqgroupinheritancespecifier: ...
    def add_group(self, qgroupid) -> Any: ...

class SubvolumeInfo(tuple):
    n_fields: ClassVar[int] = ...
    n_sequence_fields: ClassVar[int] = ...
    n_unnamed_fields: ClassVar[int] = ...
    __match_args__: ClassVar[tuple] = ...
    ctime: Incomplete
    ctransid: Incomplete
    dir_id: Incomplete
    flags: Incomplete
    generation: Incomplete
    id: Incomplete
    otime: Incomplete
    otransid: Incomplete
    parent_id: Incomplete
    parent_uuid: Incomplete
    received_uuid: Incomplete
    rtime: Incomplete
    rtransid: Incomplete
    stime: Incomplete
    stransid: Incomplete
    uuid: Incomplete
    @classmethod
    def __init__(cls, *args, **kwargs) -> None: ...
    def __reduce__(self): ...

class SubvolumeIterator:
    def __init__(self, path, top=..., info=..., post_order=...) -> newsubvolumeiterator: ...
    def close(self) -> Any: ...
    def fileno(self) -> int: ...
    def __enter__(self): ...
    def __exit__(self, type: type[BaseException] | None, value: BaseException | None, traceback: types.TracebackType | None): ...
    def __iter__(self): ...
    def __next__(self): ...

def create_snapshot(source, path, recursive=..., read_only=...,
async_=..., qgroup_inherit=...) -> Any: ...
def create_subvolume(path, async_=..., qgroup_inherit=...) -> Any: ...
def delete_subvolume(path, recursive=...) -> Any: ...
def deleted_subvolumes(path) -> Any: ...
def get_default_subvolume(path) -> int: ...
def get_subvolume_read_only(path) -> bool: ...
def is_subvolume(path) -> bool: ...
def set_default_subvolume(path, id=...) -> Any: ...
def set_subvolume_read_only(path, read_only=...) -> Any: ...
def start_sync(path) -> int: ...
def subvolume_id(path) -> int: ...
def subvolume_info(path, id=...) -> SubvolumeInfo: ...
def subvolume_path(path, id=...) -> str: ...
def sync(path) -> Any: ...
def wait_sync(path, transid=...) -> Any: ...
