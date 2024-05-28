"""Subvolume Classes and errors."""
from __future__ import annotations
from pathlib import Path
from typing import Self, TypeAlias, Callable, Iterable

from btrfsutil import SubvolumeInfo, subvolume_info, subvolume_path
from btrview.typed_info import BaseInfo, TypedInfo, BTRDICT, BASE
import btrview.btrfs as btrfs

class NotASubvolumeError(NotADirectoryError):
    """Throw when a directory isn't a subvolume"""

class Subvolume:
    """Class representing a btrfs subvolume"""
    def __init__(self, 
                 info: BaseInfo, 
                 fs: btrfs.Btrfs,
                 deleted = False) -> None:
        self.info = info
        self.fs = fs
        self.deleted = deleted

    @property
    def fs_paths(self) -> list[Path]:
        """Returns all the reachable paths of the Subvolume"""
        if self["Path"] is None:
            return []
        btr_path = self["Path"]
        paths = [mount.resolve(btr_path) for mount in self.fs.mounts if btr_path.is_relative_to(mount.fsroot)]
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
        targets = [mount.target for mount in self.fs.mounts]
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
    def from_info(cls, path: str, info: SubvolumeInfo, fs: btrfs.Btrfs) -> Self:
        t_info = TypedInfo.from_info(path, info)
        return cls(t_info, fs)

    @classmethod
    def from_ID(cls, path: str | Path, subvol_id: int, fs: btrfs.Btrfs) -> Self:
        """Creates subvolume from subvolume's ID and any path on the filesystem"""
        info = subvolume_info(path, subvol_id)
        btrfs_path = subvolume_path(path, subvol_id)
        return cls.from_info(btrfs_path, info, fs)

    @classmethod
    def from_deleted(cls, uuid: str, fs: btrfs.Btrfs):
        info = TypedInfo.from_deleted(str(uuid))
        return cls(info, fs, True)

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

class SubvolumeSieve:
    """A class for sieving subvolumes"""
    SIEVES: dict[str, Sieve] = {
            "deleted": lambda s: s.deleted,
            "root": lambda s: s.root_subvolume,
            "snapshot": lambda s: s.snapshot and not s.root_subvolume,
            "unreachable": lambda s: not (s.mounted or s.deleted),
            "non-mounts": lambda s: not s.mount_points
            }

    def __init__(self, subvolumes: list[Subvolume]) -> None:
        self.subvolumes = subvolumes

    def sieve_str(self, string_sieves: Iterable[str]):
        """Removes subvolumes from a list based on string"""
        sieves = [self.SIEVES[s] for s in string_sieves]
        return self.sieve(sieves)

    def sieve(self, remove_funcs: Iterable[Sieve]) -> list[Subvolume]:
        """Remove subvolumes from a list determined by an iterable of sieve functions"""
        to_remove = []
        for subvol in self.subvolumes:
            #if any of them evaluate True, then remove
            bools = [f(subvol) for f in remove_funcs]
            remove = any(bools)
            if remove:
                #don't want to remove in place while iterating
                to_remove.append(subvol)
        copy = self.subvolumes.copy()
        for subvol in to_remove:
            copy.remove(subvol)
        return copy

Sieve: TypeAlias = Callable[[Subvolume], bool]
