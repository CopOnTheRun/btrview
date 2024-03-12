# BTRVIEW

## Overview:

Call btrview and a filesystem label (or multiple) to and get an overview of the subvolume layout for each filesystem called. 

```
> sudo btrview HDDs
Label: HDDs
UUID: 8ad35ea1-e26b-4b2b-aea6-6b13e2a5700d
Mounts:
  /Media on /srv/media
  /Data on /srv/Data
  /Snaps on /hdd-snaps
Subvolumes:
  <FS_TREE>
  ├── Data
  ├── Media
  │   └── Pics
  └── Snaps
      ├── 2024-02-22T13:58:19.780684-05:00
      ├── 2024-02-23T02:00:19.096959-05:00
      └── 2024-02-23T11:21:54.155429-05:00
```

Call btrview with the `--snapshot` flag and you'll get the snapshot layout instead. [Wondering what the difference is?](#q-whats-the-difference-between-the-subvolume-tree-and-the-snapshot-tree)

```
sudo btrview HDDs --snapshot
Label: HDDs
UUID: 8ad35ea1-e26b-4b2b-aea6-6b13e2a5700d
Mounts:
  /Media on /srv/media
  /Data on /srv/Data
  /Snaps on /hdd-snaps
Snapshots:
  Media
  Snaps
  Data
  ├── 2024-02-22T13:58:19.780684-05:00
  ├── 2024-02-23T02:00:19.096959-05:00
  └── 2024-02-23T11:21:54.155429-05:00
  Pics
  <FS_TREE>
```

## Installation:

If you have pip installed you can grab btrview from the python package index with `pip install btrview`. Installing via pip will add the `btrview` command to your path allowing you to run the command from anywhere on the system. 

If you don't feel like installing via pip you can download it via `git clone https://github.com/CopOnTheRun/btrview` then `cd btrview`. From within the btrview directory you can run the script with `python -m btrview`. Note that if you clone the repository you'll need to make sure you have [`treelib`](https://treelib.readthedocs.io/en/latest/) installed on your system.

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

It can be nice to know which subvolumes have snapshots and how many. Even if your snapshots are scattered around a messy filesystem they'll all still show up as a nice little tree.

### Q: What's not the point of this program?

This is in no way shape or form a backup solution. Use something like [btrbk](https://github.com/digint/btrbk) for that. btrview just shows the state of things as they are, it doesn't actually "do" anything.

### Q: How is the "btr" part of btrview pronounced?

The same as the "btr" part of btrfs.

