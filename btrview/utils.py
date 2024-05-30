"""Some generic utilties to help with the module."""
import json
from pathlib import Path
import subprocess
import shlex
from os import geteuid

class NoBtrfsError(Exception):
    "Raise when there isn't a btrfs filesystem on the system"

def is_root() -> bool:
    """Check to see if the current process is running as root. If not, let the user know."""
    euid = geteuid()
    return euid == 0

def check_root() -> None:
    """Print warning message if user is not running program as root."""
    message = f"""WARNING: You're not current running this script as the root user.\nIf you have problems, try rerunning this script with sudo, or as the root user."""
    if not is_root():
        print(message)

def parse_fs_usage(path: Path) -> dict[str,int]:
    cmd = f"btrfs filesystem usage {path}"
    out = run(cmd)
    keys = "Device size,Used".split(",")
    fs_info = {}
    for line in out.stdout.splitlines()[:14]:
        if ":" not in line:
            continue
        key, val = line.split(":",maxsplit=1)
        key,val = key.strip(), val.strip()
        if val and key in keys:
            fs_info[key] = ebi_to_num(val.strip())
    return fs_info

def ebi_to_num(string: str) -> int:
    #I wonder if I'll ever have to add another entry
    conv = {"KiB":1,"MiB":2,"GiB":3,"TiB":4,"PiB":5}
    for suffix,val in conv.items():
        if suffix in string:
            return int(float(string.removesuffix(suffix))*1024**val)
    else:
        raise ValueError(f"String \"{string}\" doesn't contain an ibi-byte")

def parse_findmnt() -> list[dict[str,str]]:
    headings = "label,uuid,fsroot,target,fstype"
    cmd = f"findmnt --list --json --output {headings}"
    out = run(cmd)
    btrfs_fs = []
    for fs in json.loads(out.stdout)["filesystems"]:
        if fs["fstype"] == "btrfs":
            btrfs_fs.append(fs)
    if not btrfs_fs:
        raise NoBtrfsError("No filesystems of type btrfs could be detected.")
    return btrfs_fs

def run(command: str, **kwargs) -> subprocess.CompletedProcess[str]:
    """Split a string command into tokens, run it, and return its output."""
    tokens = shlex.split(command)
    try:
        out = subprocess.run(tokens, check=True, capture_output=True, 
                             text=True, **kwargs)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        raise e
    return out
