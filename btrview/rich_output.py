"""Functions to construct Rich objects for output to the terminal"""
import treelib

from rich.tree import Tree as RichTree
from rich.console import Group
from rich.console import Console
from rich.table import Table

from btrview.btrfs import Btrfs, get_forest
from btrview.subvolume import Subvolume

class ForestDisplay:
    def __init__(self, subvolumes: list[Subvolume]):
        self.subvolumes = subvolumes

    def display_forest(self, kind, prop, fold) -> Group:
        tree = get_forest(self.subvolumes,kind)
        sorted_forest = self.sort_forest(tree)
        rich_forest = self.rich_forest(sorted_forest, prop, fold)
        return Group(*rich_forest)

    def sort_tree(self, tree: treelib.Tree,
                  new_tree: treelib.Tree | None = None) -> treelib.Tree:
        if new_tree is None:
            root = tree.get_node(tree.root)
            new_tree = treelib.Tree()
            new_tree.add_node(root)
        subtrees = [tree.subtree(t.identifier) for t in tree.children(tree.root)]
        children = tree.children(tree.root)
        sort_func = lambda n: tree.subtree(n.identifier).size()
        sorted_children = sorted(children, key = sort_func,reverse=True)
        for child in sorted_children:
            new_tree.add_node(child,tree.root)
            subtree = tree.subtree(child.identifier)
            self.sort_tree(subtree, new_tree)
        return new_tree

    def sort_forest(self, forest: list[treelib.Tree]) -> list[treelib.Tree]:
        sort_func = lambda t: t.size()
        forest = [self.sort_tree(t) for t in forest]
        return sorted(forest, key = sort_func, reverse=True)

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

    def rich_subvol(self, subvol: Subvolume, prop: str) -> str:
        """Returns a rich formated string from subvolume output"""
        if prop and subvol[prop] is not None:
            rich_str = f"{subvol[prop]}"
        else:
            rich_str = f"{subvol}"
        if subvol.mount_points:
            rich_str = f"[bold]{rich_str}[/bold]"
        if subvol.deleted:
            rich_str = f"[red1]{rich_str}[/red1]"
        if not subvol.mounted:
            rich_str = f"[grey58]{rich_str}[/grey58]"
        return rich_str

class RichTreeTable:
    default_table_stle = {"show_edge": False, "show_lines" : False, "expand" : True, "box" : None, "padding" : 0}
    def __init__(self, title: str,subvol_forest, snapshot_forest):
        self.title = title
        self.subvol_forest = subvol_forest
        self.snapshot_forest = snapshot_forest

    def create_rich_table(self, **kwargs) -> Table:
        """Creates a table from a subvolume forest and snapshot forest"""
        if not kwargs:
            kwargs = self.default_table_stle
        forest_table = Table(title = f"{self.title}", **kwargs)
        forest_table.add_column("Subvolume Tree:")
        forest_table.add_column("Snapshot Tree:")
        forest_table.add_row(self.subvol_forest,self.snapshot_forest)
        return forest_table

def logic(labels: list[str], remove: tuple[str,...], prop: str, fold: int, export: str) -> str:
    """Constructs Rich output based on the parameters given."""
    filesystems = Btrfs.get_filesystems(labels)
    tables = []
    for fs in filesystems:
        subvols = fs.subvolumes(remove)
        display = ForestDisplay(subvols)
        subvol_display = display.display_forest("subvol", prop, fold)
        snap_display = display.display_forest("snap", prop, fold)

        forest_table = RichTreeTable(str(fs), subvol_display, snap_display).create_rich_table()
        tables.append(forest_table)
    return create_table_output(tables, export)

def create_table_output(tables: list[Table], fmt: str | None) -> str:
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

