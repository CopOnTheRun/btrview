#!/usr/bin/env python

import argparse

from rich.tree import Tree as RichTree
from rich import print
import treelib

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
        subvol_forest = get_forest([s for s in subvols if not s.deleted],"subvol")
        subvol_forest = rich_forest(subvol_forest)
        snapshot_forest = get_forest(subvols,"snap")
        snapshot_forest = rich_forest(snapshot_forest)
        for tree in subvol_forest:
            print(tree)
        for tree in snapshot_forest:
            print(tree)


def treelib_to_rich(tree: treelib.Tree, node: treelib.Node, rich_tree: RichTree) -> RichTree:
    for child in tree.children(node.identifier):
        rich_child = rich_tree.add(child.tag)
        treelib_to_rich(tree, child, rich_child)
    return rich_tree

def rich_forest(forest: list[treelib.Tree]) -> list[RichTree]:
    r_forest = []
    for tree in forest:
        root = tree.get_node(tree.root)
        rich_tree = RichTree(root.tag)
        r_forest.append(treelib_to_rich(tree,root,rich_tree))
    return r_forest

def main():
    args = parser().parse_args()
    root = "root" in args.include
    deleted = "deleted" in args.include
    unreachable = "unreachable" in args.include
    logic(args.labels, root ,deleted, unreachable, args.property)
    
if __name__ == "__main__":
    main()

