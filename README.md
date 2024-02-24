# BTRVIEW

## How to use:

Pass a filesystem label to btrview (you will most likely need root privileges) and get back a tree (or forest of trees) of snapshots with each subvolume as the root. Pass nothing and get an overview of snapshots on the whole system!

```
> sudo btrview
Label: Main
UUID: ab29fed1-b4a9-4de6-894a-816ba471ab8d
Mounts:
  /root on /
Snapshots:
  root
  └── 2024-02-23T11:21:54.065968-05:00
  chris
  └── 2024-02-23T11:21:54.096068-05:00
  portables
  machines
Label: HDDs
UUID: 8ad35ea1-e26b-4b2b-aea6-6b13e2a5700d
Mounts:
  /Media on /srv/media
  /Snaps on /hdd-snaps
  /Data on /srv/Data
Snapshots:
  Media
  Snaps
  Data
  ├── 2024-02-22T13:58:19.780684-05:00
  ├── 2024-02-23T02:00:19.096959-05:00
  └── 2024-02-23T11:21:54.155429-05:00
```

## Some Qs and As:

**Q: What is btrfs?**

A: In short, it's a copy on write (COW) filesystem. If you're not already using btrfs, then check out the [documentation](https://btrfs.readthedocs.io/en/latest/) to see if it's something you'd be interested in.

**Q: What does btrview do?**

A: It produces a tree view of the btrfs subvolumes/snapshots on your system.

**Q: So like a tree view of the subvolume layout?**

A: Nope, not currently, although it's in the works. `btrview` will show the relationship between a subvolume and its snapshots, not a relationship between a subvolume and its nested/parent subvolumes. The former is the relationship between a subvolume's UUID/Parent UUIDs, and the latter is a relationship between a subvolume's ID and Parent ID.

**Q: That's a little obscure can I get a visual example of the difference?**

A: If you run these commands

```
btrfs subvolume create subvol
btrfs subvolume create subvol/nested_subvol
btrfs subvolume snapshot subvol subvol/subvol-snap
btrfs subvolume snapshot subvol subvol/subvol-snap2
btrfs subvolume snapshot subvol/nested_subvol subvol/nested_subvol-snap
```

the subvolume tree layout would look like:

```
subvol
├── nested_subvol
├── subvol-snap
├── subvol-snap2
└── nested_subvol-snap
```

And the subvolume-snapshot relationship would look like:

```
subvol
├── subvol-snap
└── subvol-snap2
nested_subvol
└── nested_subvol-snap
```

**Q: What's the point of this program?**

A: It can be nice to know which subvolumes have snapshots and how many. Even if your snapshots are scattered around a messy filesystem they'll all still show up as a nice little tree.

**Q: What's not the point of this program?**

A: This is in no way shape or form a backup solution. Use something like [btrbk](https://github.com/digint/btrbk) for that. btrview just shows the state of things as they are, it doesn't actually "do" anything.

**Q: How is the "btr" part of btrview pronounced?**

A: The same as the "btr" part of btrfs.

## Limitations

Gonna finish writing this later...

```
> btrview
zero
└── one
    └── two
        └── three

> sudo btrfs subvolume delete one
> sudo btrview zero
zero

> sudo btrview two
9dda7e68-0741-a34f-aff7-f0e1056c1cf3
└── two
    └── three

```
