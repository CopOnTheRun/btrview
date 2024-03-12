#!/usr/bin/env python

import argparse
import textwrap

from btrview.utils import check_root
from btrview.mounts import Btrfs

def parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the command line arguments"""
    arg_parser = argparse.ArgumentParser(
            description = "Better way to view btrfs filesystems.")

    arg_parser.add_argument(
            "label",
            help="The label of the filesystem to view",
            nargs="*",)

    arg_parser.add_argument(
            "--snapshots",
            help="Whether to show snapshots",
            default = False,
            action = "store_true",)

    arg_parser.add_argument(
            "--no-root",
            help="Don't include the root subvolume",
            default = False,
            action = "store_true",)

    arg_parser.add_argument(
            "--deleted",
            help="Whether to include deleted snapshots",
            default = False,
            action = "store_true",)

    return arg_parser

def logic(labels: list[str], snapshots, root, deleted) -> None:
    check_root()
    filesystems = Btrfs.get_filesystems(labels)
    for fs in filesystems:
        print(f"{fs}")
        print("Mounts:")
        for mount in fs.mounts:
            print(f"  {mount}")
        heading = "Snapshots:" if snapshots else "Subvolumes:"
        print(heading)
        for tree in fs.forest(snapshots, root, deleted):
            print(textwrap.indent(str(tree).strip(),"  "))

def main():
    args = parser().parse_args()
    logic(args.label, args.snapshots, not args.no_root, args.deleted)
    
if __name__ == "__main__":
    main()

