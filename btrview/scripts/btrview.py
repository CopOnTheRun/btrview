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
            nargs="*")

    return arg_parser

def logic(labels: list[str]) -> None:
    check_root()
    filesystems = Btrfs.get_filesystems(labels)
    for fs in filesystems:
        print(f"{fs}")
        print("Mounts:")
        for mount in fs.mounts:
            print(f"  {mount}")
        print("Snapshots:")
        for tree in fs.snapshot_forest():
            print(textwrap.indent(str(tree).strip(),"  "))

def main():
    args = parser().parse_args()
    logic(args.label)
    
if __name__ == "__main__":
    main()

