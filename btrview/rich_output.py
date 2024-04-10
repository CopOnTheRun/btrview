"""Functions to construct Rich objects for output to the terminal"""
import treelib

from rich.tree import Tree as RichTree
from rich.console import Group
from rich.console import Console
from rich.table import Table

from btrview.btrfs import Btrfs, get_forest
from btrview.subvolume import Subvolume

def create_rich_table(title: str, subvol_forest: Group,snapshot_forest: Group) -> Table:
    """Creates a table from a subvolume forest and snapshot forest"""
    forest_table = Table(title = f"{title}", show_edge=False,
                         show_lines=False,expand=True,box=None,padding=0)
    forest_table.add_column("Subvolume Tree:")
    forest_table.add_column("Snapshot Tree:")
    forest_table.add_row(subvol_forest,snapshot_forest)
    return forest_table

def sort_tree(tree: treelib.Tree,
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
        sort_tree(subtree, new_tree)
    return new_tree

def sort_forest(forest: list[treelib.Tree]) -> list[treelib.Tree]:
    sort_func = lambda t: t.size()
    forest = [sort_tree(t) for t in forest]
    return sorted(forest, key = sort_func, reverse=True)

def logic(labels: list[str], root: bool, deleted: bool,
          unreachable:bool , prop: str, fold: int, export: str) -> str:
    """Constructs Rich output based on the parameters given."""
    filesystems = Btrfs.get_filesystems(labels)
    tables = []
    for fs in filesystems:
        subvols = fs.subvolumes(root,deleted,unreachable)

        subvol_forest = get_forest(subvols,"subvol")
        subvol_forest = sort_forest(subvol_forest)
        subvol_forest = rich_forest(subvol_forest, prop, fold)
        subvol_group = Group(*subvol_forest)

        snapshot_forest = get_forest(subvols,"snap")
        snapshot_forest = sort_forest(snapshot_forest)
        snapshot_forest = rich_forest(snapshot_forest, prop, fold)
        snapshot_group = Group(*snapshot_forest)

        forest_table = create_rich_table(str(fs),subvol_group,snapshot_group)
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

def treelib_to_rich(tree: treelib.Tree,
                    node: treelib.Node,
                    prop: str,
                    fold: int,
                    rich_tree: RichTree | None = None,
                    ) -> RichTree:
    """Creates a rich Tree from a treelib Tree"""
    if rich_tree is None:
        rich_tree = RichTree(rich_subvol(node.data, prop))
    children = tree.children(node.identifier)
    for child in children[:fold]:
        text = rich_subvol(child.data, prop)
        rich_child = rich_tree.add(text)
        treelib_to_rich(tree, child, prop, fold, rich_child)
    if fold and len(children) > fold:
        extra = len(children) - fold
        rich_tree.add(f"And {extra} more...")

    return rich_tree

def rich_subvol(subvol: Subvolume, prop: str) -> str:
    """Returns a rich formated string from subvolume output"""
    rich_str = str(subvol[prop] if subvol[prop] is not None else subvol)
    if subvol.mount_points:
        rich_str = f"[bold]{rich_str}[/bold]"
    if subvol.deleted:
        rich_str = f"[red1]{rich_str}[/red1]"
    if not subvol.mounted:
        rich_str = f"[grey58]{rich_str}[/grey58]"
    return rich_str

def rich_forest(forest: list[treelib.Tree], prop: str, fold: int) -> list[RichTree]:
    """Creates a list of Rich Trees from a list of treelib Trees"""
    r_forest = []
    for tree in forest:
        root = tree.get_node(tree.root)
        rich_tree = treelib_to_rich(tree, root, prop, fold)
        r_forest.append(rich_tree)
    return r_forest
