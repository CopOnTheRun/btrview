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

    @classmethod
    def _get_deleted_subvols(cls, subvols: list[Subvolume]) -> list[Subvolume]:
        """Returns a list of deleted subvolumes"""
        uuids = {s["UUID"] for s in subvols}
        puuids = set()
        for subvol in subvols:
            puuid = subvol["Parent UUID"]
            if puuid and (puuid not in uuids):
                puuids.add(puuid)
        return [Subvolume({"UUID":puuid}, deleted=True) for puuid in puuids]
            
    def subvolumes(self, root: bool, deleted: bool) -> list[Subvolume]:
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
            subvol = Subvolume.from_UUID(uuid,mount_point)
            subvols.append(subvol)
        if root:
            root_subvol = Subvolume.from_ID("5",mount_point)
            subvols.append(root_subvol)
        if deleted:
            subvols.extend(self._get_deleted_subvols(subvols))
        return subvols

    def forest(self, snapshots = False, root = True, deleted = False) -> list[Tree]:
        """Returns a forest of subvolumes with parent/child relationships
        being based on subvolume layout or snapshots."""
        kind = "snap" if snapshots else "subvol"
        return get_forest(self.subvolumes(root, deleted), kind)
        
    def __str__(self) -> str:
        label =  f"Label: {self.label}"
        uuid = f"UUID: {self.uuid}"
        return f"{label}\n{uuid}"

def subvol_in_list(ID: str, subvolumes: list[Subvolume], kind = "subvol") -> Subvolume | None:
    """Returns a subvolume from a list if there, else returns None."""
    key = "Subvolume ID"
    if kind == "snap":
        key = "UUID"
    for subvolume in subvolumes:
        if subvolume[key] == ID:
            return subvolume
    return None

def subvol_in_forest(ID: str, trees:list[Tree]) -> Tree | None:
    """Returns the tree containing the specified ID if there, else returns None"""
    for tree in trees:
        if ID in tree:
            return tree
    return None

def get_tree(subvol: Subvolume, subvolumes: list[Subvolume], trees: list[Tree], kind: str = "subvol") -> Tree:
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

def get_forest(subvolumes: list[Subvolume], kind = "subvol"):
    """Turns a flat list of subvolumes into a forest of trees."""
    trees: list[Tree] = []
    while subvolumes:
        subvol = subvolumes[0]
        get_tree(subvol, subvolumes, trees, kind)
    return trees
