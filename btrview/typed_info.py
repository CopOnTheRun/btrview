"""Classes and constants to aid in casting SubvolumeInfo objects."""
from pathlib import PurePath
from typing import Self
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass

from btrfsutil import SubvolumeInfo

UUIDS = {"uuid": "UUID",
         "parent_uuid": "Parent UUID",
         "received_uuid": "Received UUID",}

TIMES = {"otime": "Creation time",
         "rtime": "Receieve time",
         "stime": "Send time",
         "ctime": None,}

GENS = {"generation": "Generation",
        "otransid": "Gen at creation",
        "rtransid": "Receive transid",
        "stransid": "Send transid",
        "ctransid": None,}

INTS = {"id": "Subvolume ID",
        "parent_id": "Parent ID",
        "flags": "Flags",
        "dir_id": None,}

OTHER = {"name": "Name",
         "path": "Path",}

BTRDICT = {v:k for k,v in (UUIDS | TIMES | GENS | INTS | OTHER).items() if v}
BASE = {k:v for k,v in BTRDICT.items() if v in ("name","id","uuid")}

@dataclass
class Generation:
    """A class representing a btrfs generation"""
    generation: int

    def __lt__(self, other: Self):
        return self.generation < other.generation

@dataclass(frozen=True)
class BaseInfo:
    """Base class for TypedInfo, mainly used to facilitate creating
    subvolume and snapshot trees for subvolumes not on the filesystem"""
    name: str
    id: int
    uuid: UUID

    @classmethod
    def from_deleted(cls, suuid: str) -> "BaseInfo":
        """Returns a BaseInfo instance from a uuid"""
        uuid = UUID(suuid)
        bi = BaseInfo(suuid, uuid.int, uuid)
        return bi

    def __getitem__(self, key: str):
        """Returns the attribute corresponding to the key in BTRDICT"""
        attr = BTRDICT.get(key)
        if attr in self.__dataclass_fields__:
            return getattr(self, attr)
        else:
            return None

@dataclass(frozen=True)
class TypedInfo(BaseInfo):
    """A wrapper around SubvolumeInfo that adds type hints and convenience methods"""
    name: str
    path: PurePath
    id: int
    parent_id: int
    dir_id: int
    flags: int
    uuid: UUID
    parent_uuid: UUID
    received_uuid: UUID
    generation: Generation
    ctransid: Generation
    otransid: Generation
    stransid: Generation
    rtransid: Generation
    ctime: datetime
    otime: datetime
    rtime: datetime
    stime: datetime

    @classmethod
    def from_info(cls, path: str, info: SubvolumeInfo):
        """Returns a TypeInfo instance from a SubvolumeInfo instance"""
        kw_args = {}
        kw_args["path"] = PurePath("/" + path)
        kw_args["name"] = kw_args["path"].name or "<FS_TREE>"
        kw_args["rtime"] = info.rtime
        kw_args["stime"] = info.stime
        for attr in info.__match_args__:
            val = getattr(info, attr)
            kw_args[attr] = cls._cast(attr, val)
        return cls(**kw_args)

    @classmethod
    def _cast(cls, key: str, value: str|int|bytes) -> None | datetime | UUID | Generation | str:
        """Cast a string to its proper python type"""
        if key in TIMES:
            return datetime.fromtimestamp(value) if value else None
        elif key in UUIDS:
            value = value.hex()
            return UUID(value) if value != "0"*32 else None
        elif key in GENS:
            return Generation(value) if value else None
        elif key in INTS:
            return int(value)
        else:
            raise KeyError(f"{key = } can't be cast")
