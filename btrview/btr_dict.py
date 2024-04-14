"""Classes and functions to parse output from btrfs-progs commands."""
import re
from pathlib import Path, PurePath
from typing import Self,TypedDict,Required
from datetime import datetime
from uuid import UUID

BtrDict = TypedDict("BtrDict", {
    "Name": Required[str],
    "UUID": Required[str],
    "Subvolume ID": Required[str],
    "Parent UUID": UUID | None,
    "btrfs Path": PurePath,
    }, total = False)

class BtrfsDict:
    """Class to cast a btrfs dictionary to the correct python types"""
    def __init__(self, str_dict: dict[str, str]):
        self._str_dict = str_dict
        self.btr_dict = self.cast_dict(str_dict)

    @staticmethod
    def cast(dict_key: str, dict_value: str):
        """Cast a string to its proper python type"""
        if dict_value == "-":
            return None
        match dict_key:
            case "Creation Time"|"Send Time"|"Receive Time":
                return datetime.fromisoformat(dict_value)
            case "UUID"|"Received UUID"| "Parent UUID":
                return UUID(dict_value)
            case "Generation"|"Gen at Creation":
                return str(dict_value)
            case "btrfs Path":
                return PurePath(dict_value)
            case _:
                return dict_value

    @classmethod
    def cast_dict(cls, str_dict: dict[str,str]):
        """Casts the inputed dictionary into a properly typed btrfs dictionary"""
        new_dict = {}
        for key,val in str_dict.items():
            new_dict[key] = cls.cast(key,val)
        return new_dict

    @classmethod
    def from_list(cls, list_str: str) -> Self:
        """Turns output from `btrfs subvolume list` command into a list of subvolumes"""
        keys = "ID,gen,cgen,parent,parent_uuid,received_uuid,uuid".split(",")
        vals = "Subvolume ID,Generation,Gen at creation,Parent ID,Parent UUID,Received UUID,UUID".split(",")
        key_dict = {key:val for key,val in zip(keys,vals)}
        str_dict = {}
        for key,val in key_dict.items():
            match = re.search(f"\\b{key}\\s+(\\S+)", list_str)
            if match :
                str_dict[val] = match.group(1)
        path_match = re.search(r"path\s*(.*)",list_str).group(1).removeprefix("<FS_TREE>/")
        str_dict["btrfs Path"] = Path(f"/{path_match}")
        str_dict["Name"] = str_dict["btrfs Path"].name
        return cls(str_dict)

    @classmethod
    def from_show(cls, show_text: str) -> Self:
        """Creates btrfs prop dict based on the output of btrfs subvolume show."""
        str_dict: dict[str,str] = {}
        lines = show_text.splitlines()
        str_dict["btrfs Path"] = ("/" + lines[0]).replace("//","/")
        for line in lines[1:]:
            if re.search(r":\s+",line):
                k,v = line.split(":",maxsplit=1)
                k = k.strip()
                v = v.strip()
                str_dict[k] = v
        return cls(str_dict)

    @classmethod
    def from_deleted(cls, uuid: str) -> Self:
        """Creates a btrfs prop dict from a UUID"""
        str_dict = {"UUID":uuid,"Name":uuid,"Subvolume ID":uuid}
        return cls(str_dict)

