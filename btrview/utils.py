"""Some generic utilties to help with the module."""
import subprocess
import shlex
from pathlib import Path
from os import geteuid
from pwd import getpwuid

def is_root() -> bool:
    """Check to see if the current process is running as root. If not, let the user know."""
    euid = geteuid()
    return euid == 0

def check_root() -> None:
    """Print warning message if user is not running program as root."""
    message = f"""WARNING: You're current running this script as user {name}.\nIf you have problems, try rerunning this script with sudo, or as the root user."""
    if not is_root():
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
