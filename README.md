# BTRVIEW

## Overview:

Call btrview with a label to get an overview of the subvolume and snapshot tree layout for that specified btrfs filesystem. Call it with multiple labels and it will list each filesystem specified. Call it with no labels, and it will give an overview of every btrfs filesystem it can find.

```
> sudo btrview --labels HDDs
Label: HDDs
UUID: 8ad35ea1-e26b-4b2b-aea6-6b13e2a5700d
Subvolumes:                                       Snapshots:
  <FS_TREE>                                         Media on: /srv/media
  ├── Data on: /srv/Data                            Snaps on: /hdd-snaps
  ├── Media on: /srv/media                          2022-06-19T17:43:59.743597-04:00
  │   ├── 2024-02-01T02:00:13.760115-05:00          ├── 2022-05-13T01:49:30.487324-04:00
  │   └── Pics on: /Snaps/Testy                     │   └── 2022-05-03T23:01:29.136711-04:00
  │       └── SubVolume                             ├── 2022-06-01 15:35:50-04:00
  ├── Snaps on: /hdd-snaps                          └── 2022-06-20T15:33:57.263901-04:00
  │   ├── 2022-05-03T23:01:29.136711-04:00          Data on: /srv/Data
  │   ├── 2022-05-13T01:49:30.487324-04:00          ├── 2024-02-20T02:00:09.667556-05:00
  │   ├── 2022-06-01 15:35:50-04:00                 ├── 2024-02-21T02:00:04.595496-05:00
  │   ├── 2022-06-19T17:43:59.743597-04:00          ├── 2024-02-22T12:12:06.083575-05:00
  │   ├── 2022-06-20T15:33:57.263901-04:00          ├── 2024-02-22T12:46:11.076236-05:00
  │   ├── 2024-02-02T13:30:19.170363-05:00          ├── 2024-02-22T13:53:21.336905-05:00
  │   ├── 2024-02-20T02:00:09.667556-05:00          ├── 2024-02-22T13:57:28.944888-05:00
  │   ├── 2024-02-21T02:00:04.595496-05:00          ├── 2024-02-22T13:58:19.780684-05:00
  │   ├── 2024-02-22T12:12:06.083575-05:00          ├── 2024-02-23T02:00:19.096959-05:00
  │   ├── 2024-02-22T12:46:11.076236-05:00          └── 2024-02-23T11:21:54.155429-05:00
  │   ├── 2024-02-22T13:53:21.336905-05:00          2024-02-02T13:30:19.170363-05:00
  │   ├── 2024-02-22T13:57:28.944888-05:00          Pics on: /Snaps/Testy
  │   ├── 2024-02-22T13:58:19.780684-05:00          2024-02-01T02:00:13.760115-05:00
  │   ├── 2024-02-23T02:00:19.096959-05:00          SubVolume
  │   └── 2024-02-23T11:21:54.155429-05:00          subvolume-test
  └── subvolume-test                                <FS_TREE>
```

Wondering what the difference between the subvolume and snapshot tree is? [Check out the FAQ](#q-whats-the-difference-between-the-subvolume-tree-and-the-snapshot-tree)!

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

The main thing btrview accomplishes is providing an organized overview of a (or multiple) btrfs filesystem(s). Due to the fact btrfs relies only on loose conventions to determine where snapshots are stored, and how subvolumes are organized, it can be difficult to gain an understanding of how things are laid out. With btrview it's easy to know which subvolumes have snapshots, how many, and where they're stored. Even if your snapshots and subvolumes are scattered around a messy filesystem they'll all still show up as a nice little tree.

### Q: What's not the point of this program?

This is in no way shape or form a backup solution. Use something like [btrbk](https://github.com/digint/btrbk) for that. 

This is also not a snapshot diff viewer. If that sounds like something you're interested in check out [httm](https://github.com/kimono-koans/httm).

To put it plainly, btrview merely shows the state of things as they are, it doesn't actually "do" anything.

### Q: How is the "btr" part of btrview pronounced?

The same as the "btr" part of btrfs.

