"""Classes and functions to parse output from btrfs-progs commands."""
from pathlib import PurePath
from typing import Self,TypedDict,Required
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass

from btrfsutil import SubvolumeInfo

@dataclass
class Generation:
    """A class representing a btrfs generation"""
    generation: int

    def __lt__(self, other: Self):
        return self.generation < other.generation

BtrDict = TypedDict("BtrDict", {
    "btrfs Path": PurePath,
    "Name": Required[str],
    "Subvolume ID": Required[str],
    "UUID": Required[UUID],
    "Parent UUID": UUID | None,
    "Received UUID": UUID | None,
    "Creation time": datetime,
    "Send time": datetime | None,
    "Receive time":datetime | None,
    "Generation": Generation,
    "Gen at creation": Generation,
    "Parent ID": str,
    "Top level ID": str,
    "Flags": str,
    "Send transid": str,
    "Receive transid": str,
    }, total = False)

class BtrfsDict:
    """Class to cast a btrfs dictionary to the correct python types"""
    def __init__(self, str_dict: dict[str, str]):
        self._str_dict = str_dict
        self.btr_dict = self.cast_dict(str_dict)

    @staticmethod
    def cast(dict_key: str, dict_value: str):
        """Cast a string to its proper python type"""
        match dict_key:
            case "Creation time"|"Send time"|"Receive time":
                    if stamp := float(dict_value):
                        return datetime.fromtimestamp(stamp)
                    else:
                        return None
            case "UUID"|"Received UUID"| "Parent UUID":
                return UUID(dict_value) if dict_value != "0"*32 else None
            case "Generation"|"Gen at creation":
                return Generation(int(dict_value))
            case "btrfs Path":
                return PurePath(dict_value)
            case _:
                return dict_value

    @classmethod
    def cast_dict(cls, str_dict: dict[str,str]) -> BtrDict:
        """Casts the inputed dictionary into a properly typed btrfs dictionary"""
        new_dict = {}
        for key,val in str_dict.items():
            new_dict[key] = cls.cast(key,val)
        return new_dict

    @classmethod
    def from_deleted(cls, uuid: str) -> Self:
        """Creates a btrfs prop dict from a UUID"""
        str_dict = {"UUID":uuid,"Name":uuid,"Subvolume ID":uuid}
        return cls(str_dict)

    @classmethod
    def from_info(cls, info: SubvolumeInfo) -> Self:
        """Creates a btrfs prop dict from a SubvolumeInfo object"""
        info_attr = "uuid,parent_uuid,received_uuid,id,parent_id,otime,stime,rtime,generation,otransid,rtransid,stransid".split(",")
        show_attr = "UUID,Parent UUID,Received UUID,Subvolume ID,Parent ID,Creation time,Send time,Receieve time,Generation, Gen at creation,Receive transid,Send transid".split(",")
        str_dict = {}
        for i,s in zip(info_attr, show_attr):
            attr = getattr(info, i)
            if isinstance(attr, bytes):
                attr = attr.hex()
            str_dict[s] = str(attr)
        return cls(str_dict)
