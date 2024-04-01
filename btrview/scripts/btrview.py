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
            choices = ("root","deleted","unreachable"),
            default = ("root","unreachable"))

    arg_parser.add_argument(
            "--property",
            help = "The subvolume property to print out in the tree",
            default = None)

    return arg_parser

def logic(labels: list[str], snapshots, root, deleted, unreachable, props) -> None:
    check_root()
    filesystems = Btrfs.get_filesystems(labels)
    for fs in filesystems:
        print(f"{fs}")
        heading = "Snapshots:" if snapshots else "Subvolumes:"
        print(heading)
        for tree in fs.forest(snapshots, root, deleted, unreachable):
            #stdout=False is only needed because of bug
            #see https://github.com/caesar0301/treelib/issues/221
            tree = tree.show(data_property=props, stdout=False).strip()
            print(textwrap.indent(tree,"  "))

def main():
    args = parser().parse_args()
    root = "root" in args.include
    deleted = "deleted" in args.include
    unreachable = "unreachable" in args.include
    logic(args.labels, args.snapshots, root ,deleted, unreachable, args.property)
    
if __name__ == "__main__":
    main()

