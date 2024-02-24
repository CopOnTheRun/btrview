"""Subvolume Classes and errors."""
import subprocess
import re
from pathlib import Path, PurePath
from datetime import datetime
from typing import Self
from dataclasses import dataclass

from btrview.utils import get_UUIDs, run

class NotASubvolumeError(NotADirectoryError):
    """Throw when a directory isn't a subvolume"""

class Subvolume():
    """Class representing a BTRFS subvolume"""
    def __init__(self, path: str | Path, 
                 uuid: str| None = None,
                 root_id: str | None = None):
        """Takes a path and optional uuid, or root_id to initialize
        the subvolume instance. Not the path doesn't actually have to 
        be a direct path to the subvolume, since it's possible these
        subvolumes won't be accessible on the filesystem.."""
        self.path = path

        if uuid:
            cmd = f"btrfs subvolume show -u {uuid} {path}"
        elif root_id:
            cmd = f"btrfs subvolume show -r {root_id} {path}"
        else:
            cmd = f"btrfs subvolume show {path}"

        try:
            out = run(cmd)
        except Exception:
            raise NotASubvolumeError
        self.props = self._get_props(out.stdout)

    def _get_props(self, btrfs_show_text: str) -> dict[str,str]:
        """Creates btrfs prop dict based on the output of 
        btrfs subvolume show."""
        subvol: dict[str,str] = {}
        lines = iter(btrfs_show_text.splitlines())
        line = next(lines)
        while True:
            try:
                if re.search(r":\s+",line):
                    k,v = line.split(":",maxsplit=1)
                    k = k.strip()
                    v = v.strip()
                    v = "" if v == "-" else v
                    subvol[k] = v
                elif "Snapshot(s):" in line:
                    snapshots = []
                    line = next(lines)
                    while "Quota group:" not in line:
                        snapshots.append(line.strip())
                        line = next(lines)
                    subvol["Snapshot(s)"] = snapshots
                    continue
                line = next(lines)
            except StopIteration:
                break
        return subvol

    @staticmethod
    def is_btrfs(path: Path) -> bool:
        """Returns true if path is part of a btrfs filesystem."""
        response = run(f"btrfs filesystem usage '{path}'")
        return response.returncode == 0

    def snapshot_parent(self) -> Self | None:
        """Returns an instance of the parent snapshot if it exists."""
        if not self["Parent UUID"]:
            return None
        try:
            return type(self)(self.path, uuid=self["Parent UUID"])
        except NotASubvolumeError:
            pass
        try:
            root = type(self)(self.path, root_id="5")
            if root["UUID"] == self["Parent UUID"]:
                return root
        except NotASubvolumeError:
            pass

    def parent_subvol(self) -> Self | None:
        """Returns an instance of the parent subvolume if it exists."""
        if self["Parent ID"] == "0":
            return None
        try:
            return type(self)(self.path, root_id=self["Parent ID"])
        except NotASubvolumeError:
            pass

    def __getitem__(self, key: str) -> str:
        return self.props[key]

    def __str__(self) -> str:
        return str(self["Name"])

    def __hash__(self):
        return hash(self["UUID"])

    def __eq__(self, other):
        return self["UUID"] == other["UUID"]

class MountedSubvolume(Subvolume):
    """Class representing a mounted subvolume. Differs from a normal Subvolume
    in that it can be snapshotted and sent since there's a path to it."""
    def __init__(self, path: str|Path, 
                 uuid: str | None = None,
                 root_id: str | None = None):
        """Initialised with a path, and optionally a UUID or root id. The path
        here MUST be the path to the subvolume."""
        self.path = Path(path)
        if uuid:
            cmd = f"btrfs subvolume show -u {uuid} {path}"
        elif root_id:
            cmd = f"btrfs subvolume show -r {root_id} {path}"
        else:
            cmd = f"btrfs subvolume show {path}"
        out = run(cmd)
        if out.returncode != 0:
            raise NotASubvolumeError
        self.props = self._get_props(out.stdout)

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
        return type(self)(snap_file)

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
        return type(self)(path / self.path.name)

    def delete(self) -> None:
        """Deletes the subvolume"""
        run(f"btrfs subvolume delete '{self}'")

