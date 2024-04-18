#!/usr/bin/env python
import argparse

import btrview
from btrview.utils import check_root
from btrview.rich_output import logic,SORT_FUNCS
from btrview.btrfs import SubvolumeSieve

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
            "--exclude",
            help = "Types of subvolumes to exclude in the tree. Default is deleted. Pass the flag with no arguments to exclude no subvolumes.",
            nargs = "*",
            choices = SubvolumeSieve.SIEVES.keys(),
            default = ("deleted",))

    arg_parser.add_argument(
            "--property",
            help = "The subvolume property to print out in the tree. These are the keys from the `btrfs subvolume show` command.",)

    arg_parser.add_argument(
            "--sort",
            help = "How to sort subvolumes.",
            choices = SORT_FUNCS.keys(),
            default = "size")

    arg_parser.add_argument(
            "--ascending",
            help = "Sort ascending instead of descending",
            action = "store_true")

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
    output = logic(args.labels, args.exclude, args.property, 
                   args.fold, args.export, SORT_FUNCS[args.sort], not args.ascending)
    print(output)
 
if __name__ == "__main__":
    main()
