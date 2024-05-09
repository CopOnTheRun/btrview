# BTRVIEW

## Overview:

Call btrview with a label to get an overview of the subvolume and snapshot tree layout for that specified btrfs filesystem. Call it with multiple labels and it will list each filesystem specified. Call it with no labels, and it will give an overview of every btrfs filesystem it can find.

```
> sudo btrview --labels HDDs --fold 5
```
![btrview output](https://github.com/CopOnTheRun/btrview/raw/main/images/output.svg)

Subvolumes that are mounted (in fstab or somehow else) are in bold, those that are grey are subvolumes that aren't currently reachable on the filesystem, and subvolumes in red (not shown here) are not currently on the filesytem. This could be because they're deleted, or maybe its child subvolume was `btrfs received` from another filesystem.

Wondering what the difference between the subvolume and snapshot tree is? [Check out the FAQ](#q-whats-the-difference-between-the-subvolume-tree-and-the-snapshot-tree)!

## Installation:

Btrview relies on the following dependencies:
* python 3.11 or greater
* btrfs-progs
* python-treelib
* python-rich

The easiest way to download btrview is to use [pipx](https://pipx.pypa.io/stable/installation/) to download it from the python package index. Use the command `pipx install --system-site-packages btrview`. Using pipx to install btrview will also install the required python dependencies and add the `btrview` command to your path allowing you to run the command from anywhere on the system.

If you don't feel like installing via pipx you can download it via `git clone https://github.com/CopOnTheRun/btrview` then `cd btrview`. From within the btrview directory you can run the script with `python -m btrview`. Note that if you clone the repository you'll need to make sure you have all the dependencies installed already.

## Some Qs and As:

### Q: What is btrfs?

In short, it's a copy on write (COW) filesystem. If you're not already using btrfs, then check out the [documentation](https://btrfs.readthedocs.io/en/latest/) to see if it's something you'd be interested in.

### Q: What does btrview do?

It produces a view of the btrfs filesystems, mounts, as well as the subvolume tree or snapshot tree on your system.

### Q: What's the difference between the subvolume tree and the snapshot tree?

The subvolume tree is a tree of which subvolumes are within other subvolumes, parents being denoted by "Parent ID". The subvolume tree can be manipulated by moving subvolumes in or out of other subvolumes. The snapshot tree shows the relations between snapshots, ie snapshots taken of snapshots, etc.

If that's a little obscure here's a visual example of the difference.

If you run these commands:

```
btrfs subvolume create subvol
btrfs subvolume create subvol/nested_subvol
btrfs subvolume snapshot subvol subvol/subvol-snap
btrfs subvolume snapshot subvol subvol/subvol-snap2
btrfs subvolume snapshot subvol/nested_subvol subvol/nested_subvol-snap
```

The subvolume tree would look like:

```
subvol
├── nested_subvol
├── subvol-snap
├── subvol-snap2
└── nested_subvol-snap
```

The snapshot tree would look like:

```
subvol
├── subvol-snap
└── subvol-snap2
nested_subvol
└── nested_subvol-snap
```

### Q: What's the point of this program?

The main thing btrview accomplishes is providing an organized overview of a (or multiple) btrfs filesystem(s). Due to the fact btrfs relies only on loose conventions to determine where snapshots are stored, and how subvolumes are organized, it can be difficult to gain an understanding of how things are laid out. With btrview it's easy to know which subvolumes have snapshots, how many, and where they're stored. Even if your snapshots and subvolumes are scattered around a messy filesystem they'll all still show up as a nice little tree.

### Q: What's not the point of this program?

This is in no way shape or form a backup solution. Use something like [btrbk](https://github.com/digint/btrbk) for that. 

This is also not a snapshot diff viewer. If that sounds like something you're interested in check out [httm](https://github.com/kimono-koans/httm).

To put it plainly, btrview merely shows the state of things as they are, it doesn't actually "do" anything.

### Q: How is the "btr" part of btrview pronounced?

The same as the "btr" part of btrfs.

