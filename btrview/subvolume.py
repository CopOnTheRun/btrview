"""Subvolume Classes and errors."""
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Self

from btrview.utils import get_UUIDs, run

class NotASubvolumeError(NotADirectoryError):
    """Throw when a directory isn't a subvolume"""

class Subvolume:
    """Class representing a btrfs subvolume"""
    def __init__(self, props: dict[str,str|None], deleted: bool = False) -> None:
        self.props = props
        self.deleted = deleted

    def parent(self, p_type: str) -> str | None:
        """Returns parent UUID or ID string"""
        match p_type:
            case "snap":
                parent = self["Recieved UUID"] or self["Parent UUID"]
            case "subvol":
                parent = self["Parent ID"]
            case _:
                parent = None
        return parent

    def id(self, p_type: str) -> str | None:
        """Returns subvolume UUID or ID string"""
        match p_type:
            case "snap":
                ID = self["UUID"]
            case "subvol":
                ID = self["Subvolume ID"]
            case _:
                ID = None
        return ID

    @classmethod
    def from_UUID(cls, uuid: str, path: str | Path) -> Self:
        """Creates subvolume from the subvolumes UUID and any path on the filesystem"""
        cmd = f"btrfs subvolume show -u {uuid} {path}"
        props = cls._run_cmd(cmd)
        return cls(props)

    @classmethod
    def from_ID(cls, ID: str, path: str | Path) -> Self:
        """Creates subvolume from subvolume's ID and any path on the filesystem"""
        cmd = f"btrfs subvolume show -r {ID} {path}"
        props = cls._run_cmd(cmd)
        return cls(props)

    @classmethod
    def _run_cmd(cls, cmd: str) -> dict[str, str | None]:
        """Runs the shell command and returns the prop dictionary
        if the command doesn't error"""
        out = run(cmd)
        if out.returncode != 0:
            raise NotASubvolumeError
        props = cls._get_props(out.stdout)
        return props

    @classmethod
    def _get_props(cls, btrfs_show_text: str) -> dict[str, str | None]:
        """Creates btrfs prop dict based on the output of 
        btrfs subvolume show."""
        subvol = {}
        for line in btrfs_show_text.splitlines():
            if re.search(r":\s+",line):
                k,v = line.split(":",maxsplit=1)
                k = k.strip()
                v = v.strip()
                v = None if v == "-" else v
                subvol[k] = v
        return subvol

    @staticmethod
    def is_btrfs(path: Path) -> bool:
        """Returns true if path is part of a btrfs filesystem."""
        response = run(f"btrfs filesystem usage '{path}'")
        return response.returncode == 0

    def __getitem__(self, key: str) -> str | None:
        """Returns the item from the props dictionary, but instead
        of throwing a key error, returns None"""
        return self.props.get(key)

    def __str__(self) -> str:
        return self["Name"] or str(self["UUID"])

    def __hash__(self):
        return hash(self["UUID"])

    def __eq__(self, other):
        return self["UUID"] == other["UUID"]

class MountedSubvolume(Subvolume):
    """Class representing a mounted subvolume. Differs from a normal Subvolume
    in that it can be snapshotted and sent since there's a path to it."""
    def __init__(self, props: dict[str, str| None], path: Path):
        self.props = props
        self.path = path

    @classmethod
    def from_path(cls, path: str | Path) -> Self:
        cmd = f"btrfs subvolume show {path}"
        props = cls._run_cmd(cmd)
        path = Path(path)
        return cls(props, path)

    def same_mount(self, path: Path) -> bool:
        """Returns true if a subvolume is on the same filesystem as a specified path"""
        return get_UUIDs(self.path) == get_UUIDs(path)

    def snapshot(self, snap_dir: Path, format_str: str = "") -> Self:
        """Take a snapshot of the subvolume and save it to snap_dir"""
        if not snap_dir.is_dir():
            raise NotADirectoryError
        if format_str:
            timestamp = datetime.now().astimezone().strftime(format_str)
        else:
            timestamp = datetime.now().astimezone().isoformat()
        snap_file = snap_dir / timestamp
        out = run(f"btrfs subvolume snapshot -r '{self.path}' '{snap_file}'")
        return type(self).from_path(snap_file)

    def send(self, path: Path) -> Self:
        """Sends the subvolume to another filesystem"""
        try:
            #note that `shell=True` has some security implications with
            #user input, but figuring out how to properly do this with
            #subprocess.Popen() is not what I want to do right now.
            subprocess.run(f"btrfs send {self} | btrfs receive {path}", shell=True, check=True)
        except Exception as e:
            run(f"btrfs subvolume delete '{path}'")
            print(e)
        return type(self).from_path(path / self.path.name)

    def delete(self) -> Subvolume:
        """Deletes the subvolume"""
        run(f"btrfs subvolume delete '{self}'")
        props = {"UUID":self["UUID"]}
        return Subvolume(props,deleted=True)

