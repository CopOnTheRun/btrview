#!/usr/bin/env python
import argparse

from pathlib import Path

from btrview.utils import check_root
from btrview.subvolume import MountedSubvolume

def parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the command line arguments"""
    arg_parser = argparse.ArgumentParser(
            description = "Easier way to make and move btrfs snapshots.")

    arg_parser.add_argument(
            "subvol",
            help="The subvolume to take a snapshot of",
            type=MountedSubvolume,)
    arg_parser.add_argument(
            "directory",
            help="The directory to send the snapshot.",
            type=Path,
            nargs="?",)
    arg_parser.add_argument(
            "--send",
            help="Send these btrfs snapshots across filesystems.",
            type = Path,
            default = [],
            nargs="+")

    return arg_parser

def logic(subvol: MountedSubvolume, snap_dir: Path | None, send_dirs: list[Path]) -> None:
    check_root()
    if snap_dir and not subvol.same_mount(snap_dir):
        print(f"Subvolume {subvol['Name']} not on the same filesystem as {snap_dir}, aborting.")
        return
    snapshot = subvol.snapshot(snap_dir or subvol.path) 
    print(f"Snapshotting {snapshot}")

    for d in send_dirs:
        if subvol.same_mount(d):
            print(f"Directory {d} is on the same mount as {subvol}, skipping")
            continue
        print(f"Sending to {d}")
        snapshot.send(d)

    if not snap_dir:
        snapshot.delete()

def main():
    args = parser().parse_args()
    logic(args.subvol, args.directory, args.send)

if __name__ == "__main__":
    main()
