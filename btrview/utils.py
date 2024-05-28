"""Some generic utilties to help with the module."""
import json
import subprocess
import shlex
from os import geteuid

def is_root() -> bool:
    """Check to see if the current process is running as root. If not, let the user know."""
    euid = geteuid()
    return euid == 0

def check_root() -> None:
    """Print warning message if user is not running program as root."""
    message = f"""WARNING: You're not current running this script as the root user.\nIf you have problems, try rerunning this script with sudo, or as the root user."""
    if not is_root():
        print(message)

def parse_findmnt() -> list[dict[str,str]]:
    headings = "label,uuid,fsroot,target,fstype"
    cmd = f"findmnt --list --json --output {headings}"
    out = run(cmd)
    btrfs_fs = []
    for fs in json.loads(out.stdout)["filesystems"]:
        if fs["fstype"] == "btrfs":
            btrfs_fs.append(fs)
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
