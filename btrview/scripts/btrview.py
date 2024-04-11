#!/usr/bin/env python
import argparse

import btrview
from btrview.utils import check_root
from btrview.rich_output import logic

def parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the command line arguments"""
    arg_parser = argparse.ArgumentParser(
            description = "Better way to view btrfs filesystems.",
            epilog = f"btrview version {btrview.__version__}, created by Chris Copley")

    arg_parser.add_argument(
            "--labels",
            help="The label of the filesystem(s) to view",
            nargs="+",)

    arg_parser.add_argument(
            "--include",
            help = "Types of subvolumes to include in the tree. Default are root, unreachable and snapshot.",
            nargs = "*",
            choices = ("root","deleted","unreachable","snapshot"),
            default = ("root","unreachable","snapshot"))

    arg_parser.add_argument(
            "--property",
            help = "The subvolume property to print out in the tree. These are the keys from the `btrfs subvolume show` command.",)

    arg_parser.add_argument(
            "--fold",
            help = "Fold child output greater than N lines.",
            metavar = "N",
            type = int)

    arg_parser.add_argument(
            "--export",
            choices = ("text","svg","html"),
            help = "Export the specifed type instead of a rich table. Using this flag will still write to stdout. If you wish to save to a file use shell redirection.",)

    return arg_parser

def main():
    check_root()
    args = parser().parse_args()
    root = "root" in args.include
    deleted = "deleted" in args.include
    unreachable = "unreachable" in args.include
    snapshot = "snapshot" in args.include
    output = logic(args.labels, root, deleted, unreachable, snapshot,
                   args.property, args.fold, args.export)
    print(output)
 
if __name__ == "__main__":
    main()
