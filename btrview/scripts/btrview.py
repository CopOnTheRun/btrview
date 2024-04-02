#!/usr/bin/env python

import argparse
import textwrap
from itertools import zip_longest

import btrview
from btrview.utils import check_root
from btrview.btrfs import Btrfs, get_forest

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

def logic(labels: list[str], root, deleted, unreachable, prop) -> None:
    check_root()
    filesystems = Btrfs.get_filesystems(labels)
    for fs in filesystems:
        print(f"{fs}")
        subvols = fs.subvolumes(root,deleted,unreachable)
        subvol_tree = get_forest([s for s in subvols if not s.deleted],"subvol")
        subvol_str = get_forest_string(subvol_tree, "Subvolumes", prop)

        snap_tree = get_forest(subvols,"snap")
        snap_str = get_forest_string(snap_tree, "Snapshots", prop)

        zipper = zip_longest(subvol_str.splitlines(),snap_str.splitlines(),fillvalue="")
        for subvol_line, snap_line in zipper:
            print(f"{subvol_line:<50}{snap_line:}")

def get_forest_string(forest, header, prop: str = ""):
    forest_str = f"{header}:\n"
    for tree in forest:
        #stdout=False is only needed because of bug
        #see https://github.com/caesar0301/treelib/issues/221
        tree_str = tree.show(data_property=prop, stdout=False)
        forest_str += textwrap.indent(str(tree_str), "  ")
    return forest_str

def main():
    args = parser().parse_args()
    root = "root" in args.include
    deleted = "deleted" in args.include
    unreachable = "unreachable" in args.include
    logic(args.labels, root ,deleted, unreachable, args.property)
    
if __name__ == "__main__":
    main()

