#!/usr/bin/env python
import subprocess
import argparse
import shlex
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from os import geteuid
from pwd import getpwuid

from pandas import Series, DataFrame
from treelib import Tree

def run(command: str, **kwargs: str) -> subprocess.CompletedProcess[str]:
    """Split a string command into tokens, run it, and return its output."""
    tokens = shlex.split(command)
    out = subprocess.run(tokens, text=True, capture_output=True, **kwargs)
    return out


def parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the command line arguments"""
    arg_parser = argparse.ArgumentParser(description="Display a tree view of BTRFS snapshots.")
    arg_parser.add_argument(
        "subvol",
        nargs="?",
        help="Show the tree view of the current filesystem",
        type=Path,
    )
    arg_parser.add_argument(
        "--property",
        "-p",
        help="""Property to show in tree, eg UUID (default), Name, etc.
        Properties with spaces should replace them with underscores, eg: Parent_UUID.""",
    )

    return arg_parser


def check_root() -> None:
    """Check to see if the current process is running as root. If not, let the user know."""
    euid = geteuid()
    name = getpwuid(euid).pw_name
    message = f"""WARNING: You're current running this script as user {name}.
    If you have problems, try rerunning this script with sudo, or as the root user."""
    if euid != 0:
        print(message)


def get_UUIDs(path: Path) -> set[str]:
    """Return a set of UUIDs on a BTRFS filesystem"""
    UUIDs: set[str] = set()
    out = run(f"btrfs subvolume list -u '{path}'")
    for line in out.stdout.splitlines():
        words = line.split()
        uuid = words[words.index("uuid") + 1]
        UUIDs.add(uuid)
    return UUIDs


def subvol_attrs(path: Path, UUID: str | None = None) -> dict[str, str | None]:
    """Get the subvolume attributes from a subvolume show command"""
    if UUID:
        command = f"btrfs subvolume show '{path}' -u {UUID}"
    else:
        command = f"btrfs subvolume show '{path}'"
    out = run(command)
    return parse_subvol_show(path, out.stdout)


def parse_show_line(line: str) -> tuple[str, str | None]:
    """Parses the subvolume show line"""
    key, val = line.split(":", maxsplit=1)
    k = key.strip()
    v = None if val.strip() == "-" else val.strip()
    return k, v


def parse_subvol_show(path: Path, subvol_txt: str) -> dict[str, str | None]:
    """Parses and returns traits about the Subvolume"""
    attrs: dict[str, str | None] = {}
    lines = iter(subvol_txt.splitlines())
    attrs["Path"] = next(lines)
    for line in lines:
        if ": \t" in line:
            key, val = parse_show_line(line)
            # below is solely so that .attribute will work when this gets turned into a Series
            # The .attribute needs to work because it's the only way tree.show() will show
            # attributes other than the tag. If that constraint changes in the future,
            # this should be replaced/removed.
            key = key.replace(" ", "_")
            attrs[key] = val
    return attrs


def make_subvol_frame(path: Path) -> DataFrame:
    """Creates a subvolume DataFrame from a path which will have the contents of all subvolumes in the same filesystem as the path."""
    dict_list: dict[str, list[str | None]] = defaultdict(list)
    # the next four lines are because btrfs-list doesn't list the root tree even when mounted unless explicitly called for some reason
    subvol = subvol_attrs(path)
    if subvol["Subvolume_ID"] == "5":  # only do this if it's the root subvolume
        for key, val in subvol.items():
            dict_list[key].append(val)

    for UUID in get_UUIDs(path):
        subvol = subvol_attrs(path, UUID)
        for key, val in subvol.items():
            dict_list[key].append(val)

    frame: DataFrame = DataFrame.from_dict(dict_list)
    return frame


def get_mounts() -> list[Path]:
    """Return a list of btrfs mounts"""
    out = run("findmnt -nlt btrfs -o target")
    return [Path(p) for p in out.stdout.splitlines()]


def get_tree(uuid: str, trees: Iterable[Tree]) -> Tree | None:
    """Returns the tree that contains the uuid, else returns None"""
    for tree in trees:
        if uuid in tree:
            return tree
    return None


def get_row(uuid: str, frame: DataFrame) -> Series:
    """Returns the series from a dataframe with the matching UUID, if no match, then it returns an empty Series"""
    if uuid in frame["UUID"].values:
        return frame[frame["UUID"] == uuid].squeeze()
    return Series([None] * len(frame.columns), dtype=str, index=frame.columns)


def add_node(
    name: str, uuid: str, puuid: str, trees: list[Tree], frame: DataFrame
) -> Tree:
    """Adds a node to a tree, or creates a tree if needed, then returns the tree."""
    if tree := get_tree(uuid, trees):  # node already in tree
        return tree
    uuid_series = get_row(uuid, frame)
    if puuid:
        if tree := get_tree(puuid, trees):  # parent in tree
            tree.create_node(name, uuid, puuid, uuid_series)
        else:
            parent_series = get_row(puuid, frame)
            parent_name, parent_puuid = parent_series[["Name", "Parent_UUID"]]
            tree = add_node(parent_name, puuid, parent_puuid, trees, frame)
            tree.create_node(name, uuid, puuid, uuid_series)
    else:
        tree = Tree()
        uuid_series["UUID"] = uuid  # for deleted subvolumes
        tree.create_node(tag=name, identifier=uuid, data=uuid_series)
        trees.append(tree)
    return tree


def get_trees(path: Path) -> Iterable[Tree]:
    trees: list[Tree] = []
    frame: DataFrame = make_subvol_frame(path)
    subframe: DataFrame = frame[["Name", "UUID", "Parent_UUID"]]
    for _, row in subframe.iterrows():
        name, uuid, puuid = row
        add_node(name, uuid, puuid, trees, frame)
    return trees


def main() -> None:
    args = parser().parse_args()
    if args.subvol:
        check_root()
        trees = get_trees(args.subvol)
        for tree in trees:
            tree.show(data_property=args.property)


if __name__ == "__main__":
    main()
