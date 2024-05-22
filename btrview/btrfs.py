"""Classes and functions to interact with a btrfs filesystem."""
import json
from collections import defaultdict
from pathlib import Path, PurePath
from typing import Self, Callable, TypeAlias, Iterable
from dataclasses import dataclass

from treelib import Tree
import btrfsutil

import btrview.subvolume as sv
from btrview.utils import run

Sieve: TypeAlias = Callable[[sv.Subvolume], bool]

class SubvolumeSieve:
    """A class for sieving subvolumes"""
    SIEVES: dict[str, Sieve] = {
            "deleted": lambda s: s.deleted,
            "root": lambda s: s.root_subvolume,
            "snapshot": lambda s: s.snapshot and not s.root_subvolume,
            "unreachable": lambda s: not (s.mounted or s.deleted),
            "non-mounts": lambda s: not s.mount_points
            }

    def __init__(self, subvolumes: list[sv.Subvolume]) -> None:
        self.subvolumes = subvolumes

    def sieve_str(self, string_sieves: Iterable[str]):
        """Removes subvolumes from a list based on string"""
        sieves = [self.SIEVES[s] for s in string_sieves]
        return self.sieve(sieves)

    def sieve(self, remove_funcs: Iterable[Sieve]) -> list[sv.Subvolume]:
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
    
class Btrfs:
    """A class representing a btrfs filesystem"""
    def __init__(self, uuid: str, 
                 mounts: tuple[sv.Mount, ...],
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
        sieve = SubvolumeSieve(subvols)
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
        headings = "label,uuid,fsroot,target"
        cmd = f"findmnt --list --json --types btrfs --output {headings}"
        out = run(cmd)
        uuid_labels = {}
        uuid_mounts  = defaultdict(set)
        for j in json.loads(out.stdout)["filesystems"]:
            uuid = j['uuid']
            mount = sv.Mount(PurePath(j["fsroot"]), Path(j["target"]))
            uuid_mounts[uuid].add(mount)
            uuid_labels[j["uuid"]] = j["label"]
        filesystems = []
        for uuid in uuid_labels:
            fs = Btrfs(uuid,tuple(uuid_mounts[uuid]),uuid_labels[uuid])
            filesystems.append(fs)
        return filesystems

    @classmethod
    def from_findmt(cls, labels:list[str] | None = None) -> Self:
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

