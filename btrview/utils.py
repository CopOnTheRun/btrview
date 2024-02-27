"""Some generic utilties to help with the module."""
import subprocess
import shlex
from pathlib import Path
from os import geteuid
from pwd import getpwuid

def check_root() -> None:
    """Check to see if the current process is running as root. If not, let the user know."""
    euid = geteuid()
    name = getpwuid(euid).pw_name
    message = f"""WARNING: You're current running this script as user {name}.\nIf you have problems, try rerunning this script with sudo, or as the root user."""
    if euid != 0:
        print(message)

def run(command: str, **kwargs) -> subprocess.CompletedProcess[str]:
    """Split a string command into tokens, run it, and return its output."""
    tokens = shlex.split(command)
    try:
        out = subprocess.run(tokens, check=True, capture_output=True, 
                             text=True, **kwargs)
    except subprocess.CalledProcessError as e:
        raise e
    return out

def get_UUIDs(path: Path) -> set[str]:
    """Return a set of UUIDs on a BTRFS filesystem"""
    UUIDs: set[str] = set()
    out = run(f"btrfs subvolume list -u '{path}'")
    for line in out.stdout.splitlines():
        words = line.split()
        uuid = words[words.index("uuid") + 1]
        UUIDs.add(uuid)
    return UUIDs
