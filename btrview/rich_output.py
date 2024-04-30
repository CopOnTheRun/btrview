"""Functions and classes to construct Rich objects for output to the terminal"""
from typing import Callable, Any
from functools import partial

import treelib

from rich.tree import Tree as RichTree
from rich.console import Group
from rich.console import Console
from rich.table import Table
from rich.style import Style
from rich.text import Text

from btrview.btrfs import Btrfs, get_forest, SubvolumeSieve
from btrview.subvolume import Subvolume

TreeSorter = Callable[[treelib.Tree, treelib.Node], Any]

SORT_FUNCS: dict[str, TreeSorter]= {
        "size": lambda t,n: t.subtree(n.identifier).size(),
        "Creation time": lambda t,n: n.data["Creation time"],
        "Generation": lambda t,n: n.data["Generation"],
        "Name": lambda t,n: n.data["Name"]}

class ForestDisplay:
    """A class for working with and displaying Rich formatted trees"""
    def __init__(self, subvolumes: list[Subvolume]):
        self.subvolumes = subvolumes

    def display_forest(self, kind: str, prop: str, fold: int,
                       sort_func: TreeSorter, reverse: bool) -> Group:
        """Return the concatenated trees as a Rich Group"""
        forest = get_forest(self.subvolumes, kind)
        sorted_forest = self.sort_forest(forest, sort_func, reverse)
        rich_forest = self.rich_forest(sorted_forest, prop, fold)
        return Group(*rich_forest)

    def sort_tree(self, tree: treelib.Tree,
                  sort_func: TreeSorter,
                  reverse: bool,
                  new_tree: treelib.Tree | None = None) -> treelib.Tree:
        """Sort a tree by the specified sorting function"""
        if new_tree is None:
            root = tree.get_node(tree.root)
            new_tree = treelib.Tree()
            new_tree.add_node(root)
        children = tree.children(tree.root)
        sort_partial = partial(sort_func, tree)
        sorted_children = sorted(children, key = sort_partial, reverse = reverse)
        for child in sorted_children:
            new_tree.add_node(child,tree.root)
            subtree = tree.subtree(child.identifier)
            self.sort_tree(subtree, sort_func, reverse, new_tree)
        return new_tree

    def sort_forest(self, forest: list[treelib.Tree], sort_func: TreeSorter, reverse) -> list[treelib.Tree]:
        """Sort a forest by the specified sorting function"""
        pseudo_tree = treelib.Tree()
        pseudo_tree.create_node()
        pseudo_root = pseudo_tree.root
        for tree in forest:
            pseudo_tree.paste(pseudo_root,tree)
        sorted_pseudo = self.sort_tree(pseudo_tree, sort_func, reverse)
        sorted_forest = [sorted_pseudo.subtree(node.identifier) for node in sorted_pseudo.children(pseudo_root)]
        return sorted_forest

    def treelib_to_rich(self, tree: treelib.Tree,
                        node: treelib.Node,
                        prop: str,
                        fold: int,
                        rich_tree: RichTree | None = None,
                        ) -> RichTree:
        """Creates a rich Tree from a treelib Tree"""
        if rich_tree is None:
            rich_tree = RichTree(self.rich_subvol(node.data, prop))
        children = tree.children(node.identifier)
        for child in children[:fold]:
            text = self.rich_subvol(child.data, prop)
            rich_child = rich_tree.add(text)
            self.treelib_to_rich(tree, child, prop, fold, rich_child)
        if fold and len(children) > fold:
            extra = len(children) - fold
            string = f"And {extra} more..." if extra != 1 else f"{children[-1].data}"
            rich_tree.add(string)

        return rich_tree

    def rich_forest(self, forest: list[treelib.Tree], prop: str, fold: int) -> list[RichTree]:
        """Creates a list of Rich Trees from a list of treelib Trees"""
        r_forest = []
        for tree in forest:
            root = tree.get_node(tree.root)
            rich_tree = self.treelib_to_rich(tree, root, prop, fold)
            r_forest.append(rich_tree)
        return r_forest

    def rich_subvol(self, subvol: Subvolume, prop: str) -> Text:
        """Returns a rich formated string from subvolume output"""
        if prop and subvol[prop] is not None:
            rich_str = f"{subvol[prop]}"
        else:
            rich_str = f"{subvol}"

        sieves = SubvolumeSieve.SIEVES
        styles = []
        if not sieves["non-mounts"](subvol):
            styles.append(Style(bold=True))
        if sieves["deleted"](subvol):
            styles.append(Style(color="red1"))
        if sieves["unreachable"](subvol):
            styles.append(Style(color="grey58"))

        style = Style.combine(styles) if styles else ""
        return Text(rich_str, style)

class RichTreeTable:
    """Class to piece together Filesystem and Subvolume trees into a cohesive display"""
    default_table_style = {"show_edge": False, "show_lines" : False, "box" : None, }
    def __init__(self, title: str,subvol_forest, snapshot_forest):
        self.title = title
        self.subvol_forest = subvol_forest
        self.snapshot_forest = snapshot_forest

    def create_rich_table(self, **kwargs) -> Table:
        """Creates a table from a subvolume forest and snapshot forest"""
        if not kwargs:
            kwargs = self.default_table_style
        forest_table = Table(title = f"{self.title}", **kwargs)
        forest_table.add_column("Subvolume Tree:")
        forest_table.add_column("Snapshot Tree:")
        forest_table.add_row(self.subvol_forest,self.snapshot_forest)
        return forest_table

def logic(labels: list[str], remove: tuple[str,...], prop: str, 
          fold: int, export: str, sort_func:TreeSorter, reverse: bool) -> str:
    """Constructs Rich output based on the parameters given."""
    filesystems = Btrfs.get_filesystems(labels)
    tables = []
    for fs in filesystems:
        subvols = fs.subvolumes(remove)
        display = ForestDisplay(subvols)
        subvol_display = display.display_forest("subvol", prop, fold, sort_func, reverse)
        snap_display = display.display_forest("snap", prop, fold, sort_func, reverse)

        forest_table = RichTreeTable(str(fs), subvol_display, snap_display).create_rich_table()
        tables.append(forest_table)
    return create_table_output(tables, export)

def create_table_output(tables: list[Table], fmt: str | None) -> str:
    """Export the parameter tables to a certain format"""
    console = Console(record = True)
    captures = []
    for table in tables:
        with console.capture() as capture:
            console.print(table)
        captures.append(capture.get())
    match fmt:
        case "svg":
            out_str =  console.export_svg()
        case "text":
            out_str = console.export_text()
        case "html":
            out_str = console.export_html()
        case _:
            out_str = "".join(captures)
    return out_str
