"""Classes and functions to interact with a btrfs filesystem."""
import json
from collections import defaultdict
from pathlib import Path, PurePath
from typing import Self
from dataclasses import dataclass

from treelib import Tree
import btrfsutil

import btrview.subvolume as sv
import btrview.utils as utils

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
    
class Btrfs:
    """A class representing a btrfs filesystem"""
    def __init__(self, uuid: str, 
                 mounts: tuple[Mount, ...],
                 label: str|None = None,
                 subvolumes: list[sv.Subvolume] | None = None) -> None:
        """Initialize with the filesystem uuid, and label if it exists."""
        self.uuid = uuid
        self.mounts = mounts
        self.label = label
        self._subvolumes = subvolumes

    @property
    def default_subvolume(self) -> str:
        """Return the default subvolume for the filesystem"""
        mount = self.mounts[0]
        default = btrfsutil.get_default_subvolume(mount.target)
        return str(default)

    def _get_deleted_subvols(self, subvols: list[sv.Subvolume]) -> list[sv.Subvolume]:
        """Returns a list of deleted subvolumes"""
        uuids: set[str] = {s.id("snap") for s in subvols}
        puuids: set[str | None] = {s.parent("snap") for s in subvols if s.parent("snap")}
        deleted_puuids = puuids - uuids
        deleted_subvols = [sv.Subvolume.from_deleted(puuid, self) for puuid in deleted_puuids]
        return deleted_subvols

    def _subvol_info_iter(self,) -> list[sv.Subvolume]:
        """Returns a list of subvolume from a SubvolumeIterator"""
        subvol_iter = btrfsutil.SubvolumeIterator(self.mounts[0].target,info = True, top=5)
        subvols = []
        for path, info in subvol_iter:
            subvol = sv.Subvolume.from_info(path, info, self)
            subvols.append(subvol)
        return subvols

    def subvolumes(self, remove: tuple[str, ...]) -> list[sv.Subvolume]:
        """Return a list of subvolumes on the file system"""
        if not self._subvolumes:
            mount_point = self.mounts[0].target
            subvols = [sv.Subvolume.from_ID(mount_point, 5, self)]
            subvols.extend(self._subvol_info_iter())
            subvols.extend(self._get_deleted_subvols(subvols))
        else:
            subvols = self._subvolumes
            #mainly for testing purposes, so that I can easily pass in a list of subvolumes
        sieve = sv.SubvolumeSieve(subvols)
        return sieve.sieve_str(remove)

    def forest(self, snapshots: bool, remove: tuple[str, ...]) -> list[Tree]:
        """Returns a forest of subvolumes with parent/child relationships
        being based on subvolume layout or snapshots."""
        kind = "snap" if snapshots else "subvol"
        return get_forest(self.subvolumes(remove), kind)
        
    def __str__(self) -> str:
        return f"{self.label or self.uuid}"

    @staticmethod
    def is_btrfs(path: Path | str) -> bool:
        """Returns true if path is part of a btrfs filesystem."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"{path} doesn't exist.")
        try:
            btrfsutil.subvolume_info(path)
        except btrfsutil.BtrfsUtilError as e:
            if e.btrfsutilerror == btrfsutil.ERROR_NOT_BTRFS:
                return False
        return True

@dataclass
class System:
    filesystems: list[Btrfs]

    @classmethod
    def _get_fs(cls) -> list[Btrfs]:
        """Generates all the mount points for each filesystem"""
        json_fs = utils.parse_findmnt()
        uuid_labels = {}
        uuid_mounts  = defaultdict(set)
        for j in json_fs:
            uuid = j['uuid']
            mount = Mount(PurePath(j["fsroot"]), Path(j["target"]))
            uuid_mounts[uuid].add(mount)
            uuid_labels[j["uuid"]] = j["label"]
        filesystems = []
        for uuid in uuid_labels:
            fs = Btrfs(uuid, tuple(uuid_mounts[uuid]), uuid_labels[uuid])
            filesystems.append(fs)
        return filesystems

    @classmethod
    def from_findmnt(cls, labels:list[str] | None = None) -> Self:
        """Returns a list of each filesystem on the system."""
        filesystems = cls._get_fs()
        if labels:
            filesystems = [fs for fs in filesystems if fs.label in labels]
        return cls(filesystems)

def subvol_in_list(ID: str, subvolumes: list[sv.Subvolume], kind = "subvol") -> sv.Subvolume | None:
    """Returns a subvolume from a list if there, else returns None."""
    for subvolume in subvolumes:
        if subvolume.id(kind) == ID:
            return subvolume
    return None

def subvol_in_forest(ID: str, trees:list[Tree]) -> Tree | None:
    """Returns the tree containing the specified ID if there, else returns None"""
    for tree in trees:
        if ID in tree:
            return tree
    return None

def get_tree(subvol: sv.Subvolume, subvolumes: list[sv.Subvolume], trees: list[Tree], kind: str = "subvol") -> Tree:
    """Adds the node corresponding the the subvolume UUID/ID to the tree. If the tree
    doesn't exist, it will recursively find the root and add all corresponding nodes."""
    subvolumes.remove(subvol)
    subvol_id = subvol.id(kind) or ""
    parent_id = subvol.parent(kind) or ""
    name = str(subvol)
    if tree := subvol_in_forest(parent_id, trees):
        tree.create_node(name, subvol_id, parent_id, data=subvol)
    elif parent := subvol_in_list(parent_id, subvolumes, kind):
        tree = get_tree(parent, subvolumes, trees, kind)
        tree.create_node(name, subvol_id, parent_id, data=subvol)
    else:
        tree = Tree()
        trees.append(tree)
        tree.create_node(name, subvol_id, data=subvol)
    return tree

def get_forest(subvolumes: list[sv.Subvolume], kind = "subvol") -> list[Tree]:
    """Turns a flat list of subvolumes into a forest of trees."""
    trees: list[Tree] = []
    subvolumes = subvolumes.copy()
    while subvolumes:
        subvol = subvolumes[0]
        get_tree(subvol, subvolumes, trees, kind)
    return trees

