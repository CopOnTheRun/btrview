"""Subvolume Classes and errors."""
from pathlib import Path, PurePath
from typing import Self
from dataclasses import dataclass

from btrview.utils import run
from btrview.btr_dict import BtrDict, BtrfsDict

class NotASubvolumeError(NotADirectoryError):
    """Throw when a directory isn't a subvolume"""

@dataclass(frozen=True)
class Mount:
    """Basic class for working with mounted subvolumes."""
    fsroot: PurePath
    target: Path

    def resolve(self, path: Path) -> Path:
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
    def __init__(self, props: BtrDict, mounts: tuple[Mount, ...],
                 deleted: bool = False, show: bool = False) -> None:
        self.props = props
        self.mounts = mounts
        self.deleted = deleted
        self._show = show

    @property
    def paths(self) -> list[Path]:
        """Returns all the reachable paths of the Subvolume"""
        if self["btrfs Path"] is None:
            return []
        btr_path = Path(self["btrfs Path"])
        paths = [mount.resolve(btr_path) for mount in self.mounts if btr_path.is_relative_to(mount.fsroot)]
        paths = [path for path in paths if path.exists()]
        return paths

    @property
    def mounted(self) -> bool:
        """Returns whether the subvolume is reachable via the filesystem"""
        return bool(self.paths)

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
        return tuple(path for path in self.paths if path in targets)

    def parent(self, p_type: str) -> str | None:
        """Returns parent UUID or ID string"""
        match p_type:
            case "snap":
                parent = self["Received UUID"] or self["Parent UUID"]
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
    def from_UUID(cls, uuid: str, path: str | Path, mounts: tuple[Mount, ...]) -> Self:
        """Creates subvolume from the subvolumes UUID and any path on the filesystem"""
        cmd = f"btrfs subvolume show -u {uuid} {path}"
        props = cls._run_cmd(cmd)
        return cls(props, mounts, show = True)

    @classmethod
    def from_ID(cls, ID: str, path: str | Path, mounts: tuple[Mount, ...]) -> Self:
        """Creates subvolume from subvolume's ID and any path on the filesystem"""
        cmd = f"btrfs subvolume show -r {ID} {path}"
        props = cls._run_cmd(cmd)
        return cls(props, mounts, show = True)

    @classmethod
    def from_list(cls, list_str: str, mounts: tuple[Mount, ...]) -> Self:
        props = BtrfsDict.from_list(list_str).btr_dict
        return cls(props, mounts)

    @classmethod
    def from_deleted(cls, UUID: str) -> Self:
        """Creates subvolume from subvolume's ID and any path on the filesystem"""
        props: BtrDict = {"UUID":UUID,"Subvolume ID":UUID, "Name":UUID}
        return cls(props, tuple(), deleted=True)

    @classmethod
    def _run_cmd(cls, cmd: str) -> BtrDict:
        """Runs the shell command and returns the prop dictionary
        if the command doesn't error"""
        out = run(cmd)
        if out.returncode != 0:
            raise NotASubvolumeError
        props = BtrfsDict.from_show(out.stdout).btr_dict
        return props

    @staticmethod
    def is_btrfs(path: Path) -> bool:
        """Returns true if path is part of a btrfs filesystem."""
        response = run(f"btrfs filesystem usage '{path}'")
        return response.returncode == 0

    def __getitem__(self, key: str) -> str | None:
        """Returns the item from the props dictionary, but instead
        of throwing a key error, returns None"""
        if key in self.props:
            return self.props[key]
        elif self.deleted:
            #just assume it's None for deleted subvols. #could cause problems
            #in that deleted Subvolumes won't throw KeyError
            return None
        elif not self._show:
            cmd = f"btrfs subvolume show -u {self['UUID']} {self.mounts[0].target}"
            props = self._run_cmd(cmd)
            self.props |= props
            self._show = True
        try:
            return self.props[key]
        except KeyError:
            pass
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
