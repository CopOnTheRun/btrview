#!/usr/bin/env python

import argparse
import textwrap

import btrview
from btrview.utils import check_root
from btrview.btrfs import Btrfs

def parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the command line arguments"""
    arg_parser = argparse.ArgumentParser(
            description = "Better way to view btrfs filesystems.",
            epilog = f"btrview version {btrview.__version__}, created by Chris Copley")

    arg_parser.add_argument(
            "--labels",
            help="The label of the filesystem to view",
            nargs="+",)

    arg_parser.add_argument(
            "--snapshots",
            help="Whether to show snapshots",
            default = False,
            action = "store_true",)

    arg_parser.add_argument(
            "--include",
            help = "Types of subvolumes to include in the tree",
            nargs = "*",
            choices = ("root","deleted",),
            default = ("root",))

    return arg_parser

def logic(labels: list[str], snapshots, root, deleted) -> None:
    check_root()
    filesystems = Btrfs.get_filesystems(labels)
    for fs in filesystems:
        print(f"{fs}")
        print("Mounts:")
        for mount in sorted(fs.mounts, key=lambda fs: (fs.fsroot, fs.target)):
            print(f"  {mount}")
        heading = "Snapshots:" if snapshots else "Subvolumes:"
        print(heading)
        for tree in fs.forest(snapshots, root, deleted):
            print(textwrap.indent(str(tree).strip(),"  "))

def main():
    args = parser().parse_args()
    logic(args.labels, args.snapshots, "root" in args.include, "deleted" in args.include)
    
if __name__ == "__main__":
    main()

