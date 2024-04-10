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
            default = "Name")

    arg_parser.add_argument(
            "--export",
            choices = ("text","svg","html"),
            help = "Export to specifed type instead of table",)

    arg_parser.add_argument(
            "--fold",
            help = "Fold child output greater than N lines.",
            metavar = "n",
            type = int)
    return arg_parser

def main():
    check_root()
    args = parser().parse_args()
    root = "root" in args.include
    deleted = "deleted" in args.include
    unreachable = "unreachable" in args.include
    output = logic(args.labels, root, deleted, unreachable, args.property, args.fold, args.export)
    print(output)
    
if __name__ == "__main__":
    main()
