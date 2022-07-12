# BTRVIEW

## How to use:

Pass a subvolume to btrview (you will most likely need root privileges) and get back a tree (or forest of trees) of snapshots with each subvolume as the root. Optionally add the `--property` flag to show the same tree view, but instead of showing each subvolume's name, show a different property like the parent UUID, or generation.

```
> sudo btrview /

home
├── 2022-04-03T11:43:33.299005-04:00
│   └── 2022-04-04T13:43:58.390132-04:00 <- snapshot of a snapshot
├── 2022-04-04T10:52:40.092005-04:00
├── 2022-04-04T12:13:43.674322-04:00
├── 2022-04-04T13:45:33.000768-04:00
└── 2022-04-24T15:35:36.923988-04:00

root
├── 2022-04-03T12:45:08.681841-04:00
├── 2022-04-04T14:10:21.514867-04:00
└── 2022-04-23T15:35:21.581229-04:00

machines

portables

> sudo btrview / --property Parent_UUID

None
├── 784e1c69-afef-f047-b86a-f6afd14efc5c
│   └── 2b3261ef-f161-bf4e-9688-40728879360d
├── 784e1c69-afef-f047-b86a-f6afd14efc5c
├── 784e1c69-afef-f047-b86a-f6afd14efc5c
├── 784e1c69-afef-f047-b86a-f6afd14efc5c
└── 784e1c69-afef-f047-b86a-f6afd14efc5c

None
├── ceb25142-556f-fc43-8041-986a5a67a503
├── ceb25142-556f-fc43-8041-986a5a67a503
└── ceb25142-556f-fc43-8041-986a5a67a503
```

## Some Qs and As:

**Q: What is btrfs?**

A: In short, it's a copy on write (COW) filesystem. If you're not already using btrfs, then check out the [documentation](https://btrfs.readthedocs.io/en/latest/) to see if it's something you'd be interested in.

**Q: What does btrview do?**

A: It produces a tree view of the btrfs subvolumes/snapshots on your system.

**Q: So like a tree view of the subvolume layout?**

A: Nope, not at all. This will show the relationship between a subvolume and its snapshots, not a relationship between a subvolume and its nested/parent subvolumes. The former is the relationship between a subvolume's UUID/Parent UUIDs, and the latter is a relationship between a subvolume's ID and Parent ID.

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

**Q: What inputs will the `--property` flag take?**

A: The same listed in the `btrfs subvolume show` command with the caveat that spaces need to be changed to underscores. Also the snapshots property won't work, because well that's essentially what the tree is showing.

**Q: When using the `--property` flag why do some of the tree nodes say None?**

A: Some subvolumes won't have a certain property. For example subvolumes made with `btrfs subvolume create` won't have a Parent UUID and subvolumes that haven't been `btrfs receive`'d won't have a recieve time or received UUID. Usually the other cases are those described in the [limitations](#limitations) section.

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

## Needs Fixin'

- [ ] The path property not being reported correctly
- [ ] Doesn't work if the passed path isn't a subvolume
- [ ] arguments passed to `--property` need underscores where spaces are right now
- [ ] The current method of adding a subvolume to a tree could be updated so that it doesn't try to add subvolumes that are already in the tree.
- [ ] I'm pretty sure this isn't pep 8 compliant
- [ ] I'm pretty sure the typing could be shored up
- [ ] Currently a pandas Dataframe is used to tabulate things, and I don't think there's really a need to pull pandas in as a dependency.
- [ ] Could be more object oriented


## Needs implementin'

- [ ] Show the relationship between snapshots even if the snapshot is on another btrfs filesystem (ie from btrfs send/recieve)
- [ ] Ability to show only specified subvolume tree instead of all of them
- [ ] Option to omit showing deleted subvolumes
- [ ] Option to show subvolume layout (ID-Parent ID) relationship
- [ ] Option for different outputs instead of tree view, like a list view based on the root of a tree
- [ ] asyncronous?
