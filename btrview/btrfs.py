"""Classes and functions to interact with a btrfs filesystem."""
import json
from collections import defaultdict
from pathlib import Path, PurePath
from typing import Self, Callable, TypeAlias, Iterable

from treelib import Tree
import btrfsutil

from btrview.utils import run
from btrview.subvolume import Subvolume, Mount

Sieve: TypeAlias = Callable[[Subvolume], bool]

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

    @property
    def default_subvolume(self) -> str:
        """Return the default subvolume for the filesystem"""
        mount = self.mounts[0]
        default = btrfsutil.get_default_subvolume(mount.target)
        return str(default)

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
        puuids: set[str | None] = {s.parent("snap") for s in subvols if s.parent("snap")}
        deleted_puuids = puuids - uuids
        deleted_subvols = [Subvolume.from_deleted(puuid) for puuid in deleted_puuids]
        return deleted_subvols

    def _subvol_info_iter(self,) -> list[Subvolume]:
        """Returns a list of subvolume from a SubvolumeIterator"""
        subvol_iter = btrfsutil.SubvolumeIterator(self.mounts[0].target,info = True, top=5)
        subvols = []
        for path, info in subvol_iter:
            subvol = Subvolume.from_info(path, info, self.mounts)
            subvols.append(subvol)
        return subvols

    def subvolumes(self, remove: tuple[str, ...]) -> list[Subvolume]:
        """Return a list of subvolumes on the file system"""
        mount_point = self.mounts[0].target 
        subvols = [] if "root" in remove else [Subvolume.from_ID(mount_point,5, self.mounts)]
        subvols.extend(self._subvol_info_iter())
        subvols.extend(self._get_deleted_subvols(subvols))
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

