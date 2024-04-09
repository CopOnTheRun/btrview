from rich.tree import Tree as RichTree
from rich.console import Group
from rich.console import Console
from rich.table import Table
import treelib

from btrview.btrfs import Btrfs, get_forest
from btrview.subvolume import Subvolume

def logic(labels: list[str], root, deleted, unreachable, prop, export) -> str | None:
    filesystems = Btrfs.get_filesystems(labels)
    for fs in filesystems:
        subvols = fs.subvolumes(root,deleted,unreachable)
        subvol_forest = get_forest(subvols,"subvol")
        subvol_forest = rich_forest(subvol_forest, prop)
        snapshot_forest = get_forest(subvols,"snap")
        snapshot_forest = rich_forest(snapshot_forest, prop)

        forest_table = Table(title = f"{fs}", show_edge=False,
                             show_lines=False,expand=True,box=None,padding=0)
        forest_table.add_column("Subvolume Tree:")
        forest_table.add_column("Snapshot Tree:")
        forest_table.add_row(subvol_forest,snapshot_forest)

        console = Console(record = True)
        with console.capture() as capture:
            console.print(forest_table)
        match export:
            case "svg":
                return console.export_svg()
            case "text":
                return console.export_text()
            case "html":
                return console.export_html()
            case _:
                return capture.get()

def treelib_to_rich(tree: treelib.Tree,
                    node: treelib.Node,
                    prop: str,
                    rich_tree: RichTree | None = None,
                    ) -> RichTree:
    if rich_tree is None:
        rich_tree = RichTree(rich_subvol(node.data, prop))
    for child in tree.children(node.identifier):
        text = rich_subvol(child.data, prop)
        rich_child = rich_tree.add(text)
        treelib_to_rich(tree, child, prop, rich_child)
    return rich_tree


def rich_subvol(subvol: Subvolume, prop: str) -> str:
    rich_str = str(subvol[prop] if subvol[prop] is not None else subvol)
    if subvol.mount_points:
        rich_str = f"[bold]{rich_str}[/bold]"
    if subvol.deleted:
        rich_str = f"[red1]{rich_str}[/red1]"
    if not subvol.mounted:
        rich_str = f"[grey58]{rich_str}[/grey58]"
    return rich_str

def rich_forest(forest: list[treelib.Tree], prop) -> Group:
    r_forest = []
    for tree in forest:
        root = tree.get_node(tree.root)
        r_forest.append(treelib_to_rich(tree, root, prop))
    rich_group = Group(*r_forest)
    return rich_group
