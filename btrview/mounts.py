"""Classes and functions to interact with a btrfs filesystem."""
import json
import re
from collections import defaultdict
from pathlib import Path, PurePath
from typing import Self
from dataclasses import dataclass

from treelib import Tree

from btrview.utils import run
from btrview.subvolume import Subvolume

@dataclass(frozen=True)
class Mount:
    """Basic class for working with mounted subvolumes."""
    fsroot: PurePath
    target: Path

    def resolve(self, path: str) -> Path:
        """Returns the resolved path of another path"""
        fsroot_str = str(self.fsroot)
        target_str = str(self.target)
        path_str = str(path)
        new_path = path_str.replace(fsroot_str,target_str,1).replace("//","/",1)
        return Path(new_path)

    def __str__(self):
        return f"{self.fsroot} on {self.target}"

class Btrfs:
    """A class representing a btrfs filesystem"""
    _UUIDs:  dict[str,str] = dict()
    _all_mounts: defaultdict[str,set[Mount]] = defaultdict(set)

    def __init__(self, uuid: str, label: str|None = None):
        """Initialist with the filesystem uuid, and label if it exists."""
        self.uuid = uuid
        self.label = label
        self._get_mounts()

    @classmethod
    def _get_mounts(cls):
        """Generates all the mount points for each filesystem"""
        headings = "label,uuid,fsroot,target"
        #Why parse all mounts instead of just one using the --source flag?
        #Some of the FSes weren't showing up for some reason with that flag. Also
        #it would mean running the command for every FS. Unfortunately if this 
        #method isn't run, then self.mounts will incorrectly return an empty list.
        cmd = f"findmnt --list --json --types btrfs --output {headings}"
        out = run(cmd)
        for j in json.loads(out.stdout)["filesystems"]:
            uuid = j['uuid']
            mount = Mount(PurePath(j["fsroot"]),Path(j["target"]))
            cls._all_mounts[uuid].add(mount)
            cls._UUIDs[j["uuid"]] = j["label"]

    @property
    def mounts(self) -> tuple[Mount,...]:
        """Returns the mounts for a certain filesystem as a tuple."""
        #cast to tuple makes for easier referencing, also has the benefit of
        #preventing direct access to the set object
        return tuple(self._all_mounts[self.uuid])

    @classmethod
    def get_filesystems(cls, labels:list[str] | None = None) -> list[Self]:
        """Returns a list of each filesystem on the system."""
        cls._get_mounts() #had to be here in case nothing gets initialized
        filesystems = []
        for uuid,label in cls._UUIDs.items():
            if not labels or (label in labels):
                fs = cls(uuid,label)
                filesystems.append(fs)
        return filesystems

    def subvolumes(self) -> list[Subvolume]:
        """Return a list of subvolumes on the file system"""
        mount_point = self.mounts[0].target 
        out = run(f"btrfs subvolume list -u {mount_point}")
        fs_uuids = []
        subvols = []
        for line in out.stdout.splitlines():
            match = re.search(r"uuid\s*(\S*)",line)
            if match:
                fs_uuids.append(match.group(1))
        for uuid in fs_uuids:
            subvol = Subvolume(mount_point,uuid)
            subvols.append(subvol)
        root_subvol = Subvolume(mount_point,root_id="0")
        if root_subvol not in subvols:
            subvols.append(root_subvol)
        return subvols

    def snapshot_forest(self) -> list[Tree]:
        """Returns a list of snapshot trees in the filesystem."""
        return get_forest(self.subvolumes())
        
    def __str__(self) -> str:
        label =  f"Label: {self.label}"
        uuid = f"UUID: {self.uuid}"
        return f"{label}\n{uuid}"

def pop_subvol(uuid: str, subvolumes: list[Subvolume]) -> Subvolume | None:
    """Removes a subvolume from a list and returns it"""
    for subvolume in subvolumes:
        if subvolume["UUID"] == uuid:
            subvolumes.remove(subvolume)
            return subvolume

def node_in_forest(subvol_uuid: str, trees:list[Tree]) -> Tree | None:
    """Returns the tree the subvolume UUID is in, if there is one."""
    for tree in trees:
        if subvol_uuid in tree:
            return tree

def get_tree(subvol_uuid: str, subvolumes: list[Subvolume], trees: list[Tree]) -> Tree:
    """Adds the node corresponding the the subvolume UUID to the tree. If the tree
    doesn't exist, it will recursively find the root and add all corresponding nodes."""
    subvol = pop_subvol(subvol_uuid,subvolumes)
    if subvol and (parent := subvol["Parent UUID"]):
        tree = node_in_forest(parent,trees) or get_tree(parent,subvolumes,trees)
        tree.create_node(subvol["Name"],subvol["UUID"],parent,data=subvol)
        return tree
    else:
        new_tree = Tree()
        name = subvol["Name"] if subvol else subvol_uuid
        new_tree.create_node(name,subvol_uuid)
        trees.append(new_tree)
        return new_tree

def get_forest(subvolumes: list[Subvolume]):
    """Turns a flat list of subvolumes into a forest of trees."""
    trees: list[Tree] = []
    while subvolumes:
        subvol = subvolumes[0]
        get_tree(subvol["UUID"],subvolumes,trees)
    return trees
