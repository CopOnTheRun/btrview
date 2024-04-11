"""Classes and functions to interact with a btrfs filesystem."""
import json
import re
from collections import defaultdict
from pathlib import Path, PurePath
from typing import Self, Callable, TypeAlias

from treelib import Tree

from btrview.utils import run
from btrview.subvolume import Subvolume, Mount

SubvolumeSieve: TypeAlias = Callable[[Subvolume], bool]

class Btrfs:
    """A class representing a btrfs filesystem"""
    _UUIDs:  dict[str,str] = dict()
    _all_mounts: defaultdict[str,set[Mount]] = defaultdict(set)

    def __init__(self, uuid: str, label: str|None = None) -> None:
        """Initialist with the filesystem uuid, and label if it exists."""
        self.uuid = uuid
        self.label = label
        if not self._UUIDs:
            self._get_mounts()

    @classmethod
    def _get_mounts(cls) -> None:
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
        #had to be here in case nothing gets initialized
        if not cls._UUIDs:
            cls._get_mounts() 
        filesystems = []
        for uuid,label in cls._UUIDs.items():
            if not labels or (label in labels):
                fs = cls(uuid,label)
                filesystems.append(fs)
        return filesystems

    @classmethod
    def _get_deleted_subvols(cls, subvols: list[Subvolume]) -> list[Subvolume]:
        """Returns a list of deleted subvolumes"""
        uuids: set[str] = {s.id("snap") for s in subvols}
        puuids: set[str] = {s.parent("snap") for s in subvols if s.parent("snap")}
        deleted_puuids = puuids - uuids
        deleted_subvols = [Subvolume.from_deleted(puuid) for puuid in deleted_puuids]
        return deleted_subvols

    def _parse_subvol_list(self, list_str: str) ->list[Subvolume]:
        """Turns output from `btrfs subvolume list` command into a list of subvolumes"""
        subvols = []
        keys = "ID,gen,cgen,parent,parent_uuid,received_uuid,uuid".split(",")
        vals = "Subvolume ID,Generation,Gen at creation,Parent ID,Parent UUID,Received UUID,UUID".split(",")
        key_dict = {key:val for key,val in zip(keys,vals)}
        for line in list_str.splitlines():
            match_dict = {}
            for key,val in key_dict.items():
                match = re.search(f"\\b{key}\\s+(\\S+)",line)
                if match and match.group(1) == "-":
                    match_dict[val] = None
                elif match :
                    match_dict[val] = match.group(1)
            path_match = re.search(r"path\s*(.*)",line).group(1).removeprefix("<FS_TREE>/")
            match_dict["btrfs Path"] = Path(f"/{path_match}")
            match_dict["Name"] = match_dict["btrfs Path"].name
            subvols.append(Subvolume(match_dict,self.mounts))
        return subvols

    def subvolumes(self, root: bool, deleted: bool, unreachable: bool, snapshot: bool) -> list[Subvolume]:
        """Return a list of subvolumes on the file system"""
        mount_point = self.mounts[0].target 
        subvols = [] if root else [Subvolume.from_ID("5",mount_point, self.mounts)]
        out = run(f"sudo btrfs subvolume list -apcguqR {mount_point}")
        subvols.extend(self._parse_subvol_list(out.stdout))
        subvols.extend(self._get_deleted_subvols(subvols))

        funcs: list[SubvolumeSieve] = []
        if unreachable:
            funcs.append(lambda s: not (s.mounted or s.deleted or s.root_subvolume))
        if snapshot:
            funcs.append(lambda s: s.snapshot and not s.root_subvolume)
        if deleted:
            funcs.append(lambda s: s.deleted)
        remove_subvols(subvols, funcs)
        return subvols

    def forest(self, snapshots = False, root = True, deleted = False,
               unreachable = True, snapshot = True) -> list[Tree]:
        """Returns a forest of subvolumes with parent/child relationships
        being based on subvolume layout or snapshots."""
        kind = "snap" if snapshots else "subvol"
        return get_forest(self.subvolumes(root, deleted, unreachable, snapshot), kind)
        
    def __str__(self) -> str:
        return f"{self.label or self.uuid}"

def subvol_in_list(ID: str, subvolumes: list[Subvolume], kind = "subvol") -> Subvolume | None:
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

def get_forest(subvolumes: list[Subvolume], kind = "subvol") -> list[Tree]:
    """Turns a flat list of subvolumes into a forest of trees."""
    trees: list[Tree] = []
    subvolumes = subvolumes.copy()
    while subvolumes:
        subvol = subvolumes[0]
        get_tree(subvol, subvolumes, trees, kind)
    return trees

def remove_subvols(subvols: list[Subvolume], remove_funcs: list[SubvolumeSieve]):
    """Remove subvolumes from a list determined by a list of sieve functions"""
    to_remove = []
    for subvol in subvols:
        #if any of them evaluate True, then remove
        bools = [f(subvol) for f in remove_funcs]
        remove = any(bools)
        if remove:
            #don't want to remove in place while iterating
            to_remove.append(subvol)
    for subvol in to_remove:
        subvols.remove(subvol)
