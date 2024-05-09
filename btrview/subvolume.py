"""Subvolume Classes and errors."""
from pathlib import Path, PurePath
from typing import Self
from dataclasses import dataclass

from btrfsutil import SubvolumeInfo, subvolume_info, subvolume_path
from btrview.typed_info import BaseInfo, TypedInfo, BTRDICT, BASE

class NotASubvolumeError(NotADirectoryError):
    """Throw when a directory isn't a subvolume"""

@dataclass(frozen=True)
class Mount:
    """Basic class for working with mounted subvolumes."""
    fsroot: PurePath
    target: Path

    def resolve(self, path: PurePath) -> Path:
        """Returns the resolved path of another path"""
        fsroot_str = str(self.fsroot)
        target_str = str(self.target)
        if fsroot_str == "/":
            target_str = target_str + "/"
        path_str = str(path)
        new_path = path_str.replace(fsroot_str,target_str,1).replace("//","/",1)
        return Path(new_path)

    def __str__(self) -> str:
        return f"{self.fsroot} on {self.target}"

class Subvolume:
    """Class representing a btrfs subvolume"""
    def __init__(self, 
                 info: BaseInfo, 
                 mounts: tuple[Mount, ...],
                 deleted = False) -> None:
        self.info = info
        self.mounts = mounts
        self.deleted = deleted

    @property
    def fs_paths(self) -> list[Path]:
        """Returns all the reachable paths of the Subvolume"""
        if self["Path"] is None:
            return []
        btr_path = self["Path"]
        paths = [mount.resolve(btr_path) for mount in self.mounts if btr_path.is_relative_to(mount.fsroot)]
        paths = [path for path in paths if path.exists()]
        return paths

    @property
    def mounted(self) -> bool:
        """Returns whether the subvolume is reachable via the filesystem"""
        return bool(self.fs_paths)

    @property
    def root_subvolume(self) -> bool:
        """Returns whether the subvolume is the root_subvolume"""
        return self["Subvolume ID"] == "5"

    @property
    def snapshot(self) -> bool:
        """Returns whether the subvolume is a snapshot"""
        return bool(self["Parent UUID"])

    @property
    def mount_points(self) -> tuple[Path, ...]:
        """Returns mount points of Subvolume"""
        targets = [mount.target for mount in self.mounts]
        return tuple(path for path in self.fs_paths if path in targets)

    def parent(self, p_type: str) -> str | None:
        """Returns parent UUID or ID string"""
        match p_type:
            case "snap":
                parent = self["Parent UUID"]
            case "subvol":
                parent = self["Parent ID"]
            case _:
                parent = None
        return parent

    def id(self, p_type: str) -> str:
        """Returns subvolume UUID or ID string"""
        match p_type:
            case "snap":
                ID = self["UUID"]
            case "subvol":
                ID = self["Subvolume ID"]
            case _:
                ID = self["UUID"]
        return ID

    @classmethod
    def from_info(cls, path: str, info: SubvolumeInfo, mounts: tuple[Mount, ...]) -> Self:
        t_info = TypedInfo.from_info(path, info)
        return cls(t_info, mounts)

    @classmethod
    def from_ID(cls, path: str | Path, subvol_id: int, mounts: tuple[Mount, ...]) -> Self:
        """Creates subvolume from subvolume's ID and any path on the filesystem"""
        info = subvolume_info(path, subvol_id)
        btrfs_path = subvolume_path(path, subvol_id)
        return cls.from_info(btrfs_path, info, mounts)

    @classmethod
    def from_deleted(cls, uuid: str):
        info = TypedInfo.from_deleted(str(uuid))
        return cls(info, (), True)

    def __getitem__(self, key: str) -> str | None:
        """Returns the item from TypedInfo object."""
        if key in BTRDICT:
            if not self.deleted:
                return self.info[key]
            else:
                return self.info[key] if key in BASE else None
        else:
            try:
                return getattr(self, key)
            except AttributeError:
                raise KeyError(f"Subvolume has no attribute or key '{key}'")

    def __str__(self) -> str:
        string = self["Name"]
        if mps := self.mount_points:
            mp_string = ", ".join(str(mp) for mp in mps)
            string = f"{string} on: {mp_string}"
        return str(string)

    def __hash__(self) -> int:
        return hash(self["UUID"])

    def __eq__(self, other) -> bool:
        return self["UUID"] == other["UUID"]


