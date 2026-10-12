# 3. Levels, rooms and topology

## Room size and word layout

Every gameplay room is **20 tiles × 11 tiles**. Each source square stores one big-endian **16-bit word** (normally tile ID, sometimes an entity/control marker). The older 20×12 gameplay-room interpretation is incorrect: 20×12 is the *separate* front-end faux-room.

## Logical versus physical rooms — verified data

There are exactly **150 physical gameplay rooms**. Levels 1–3 keep logical room addresses separately from physical room data; Level 4 has a direct eight-wide grid.

| Level | Physical rooms | Logical slots | Active logical slots | Lookup runtime address |
|---|---:|---:|---:|---|
| 1 | 15 | 24 (3×8) | 15 | `$3FD66` |
| 2 | 23 | 32 (4×8) | 23 | `$3FD96` |
| 3 | 32 | 32 (4×8) | 32 | `$3FDD6` |
| 4 | 80 | 80 (10×8) | 80 | Direct, no lookup table |

A logical room number can exceed the highest physical index. For instance Level 2 logical room 24 is valid although there are only 23 physical rooms. The game looks up the **physical** room to render and load. Inactive logical slots contain real zero table entries, **not** invalid-room sentinels.

### Level 1 logical active slots

```text
 0  1  2  3  4
 8  9 10 11 12
16 17 18 19 20
```

### Level 2 logical active slots

```text
 0  1  2  3  4  5
 8  9 10 11 12 13
16 17 18 19 20 21
24 25 26 27 28
```

All 0–31 logical slots in Level 3 and all 0–79 slots in Level 4 are active in the current original layout.

## Physical storage and address equations

**Levels 1–3** store rows interleaved across physical rooms, *not* 20×11 room blocks:

```text
runtime_word = map_base + physical_room * $28
                         + tile_y * row_stride + tile_x * 2
```

| Level | Map base | Source row stride |
|---|---|---|
| 1 | `$4084A` | `$25A` |
| 2 | `$42228` | `$398` |
| 3 | `$449B0` | `$500` |

`$28` is the byte count for 20 source words. Level 1 contains **one extra padding word after the 15 physical rows** on each of the 11 tile scanlines; preserve it.

**Level 4** is directly organised as an eight-room-wide grid:

```text
runtime_word = $480B0 + (physical_room >> 3) * $DC0
                      + (physical_room & 7) * $28
                      + tile_y * $140 + tile_x * 2
```

In the currently documented GAME image, **file offset = runtime address − `$EE06`**. This offset is the reverse-engineering model's relocated-image mapping, not an Amiga address-space permission to write arbitrary code/data.

The extracted model and HTML5 first release read the level descriptors for Levels 1–3 at `$3FD4E` (three records, eight bytes each: lookup pointer `.l`, map pointer `.l`); the four 32-bit strides begin at `$3FFC0`. The v0.2 HTML5 application checks these against the supported profile before allowing any editing.

## Moving between rooms — verified current behaviour

Normal room transitions adjust the logical room number by **right `+1`, left `-1`, up `-8`, down `+8`**. The game also remembers the previously visited room and rejects an immediate transition back into it. Opening a route into a presently inactive logical slot may therefore access an unexpected physical room rather than safely failing.

This explains why **moving rooms around in a level map is not inherently the same thing as changing the visible lookup table**. Any authoring of different topologies must consider exit tests, active-slot selection, adjacency, special references and storage capacity.

## Start rooms

The start-room table is at `$3FFB8` (four 16-bit logical room IDs):

```text
Level 1 = 0
Level 2 = 3
Level 3 = 1
Level 4 = 9
```

One `$02B` START marker is also present in each level. Editing a lookup may change which physical room is associated with the logical start location. An editor must keep both concepts coherent.

## HTML5 migration and future topology authoring

**Source:** `tools/cybernoid_project.py`: `LEVELS`, `room_cell_runtime()`, `extract_project()`; converted to `app/cybernoid-data.js`: `CONFIG`, `Game.roomAddress()`, `Game.physical()`. These source references help developers verify the decoded fields; the above is game data, not a proposal for its format.

The browser UI deliberately separates the **logical grid shown at left** from **physical-room data** and from eventual **transition controls**. Logical room navigation is currently functional, but topology mutation is **read-only**. This is an important design constraint for future expansions: active-slot flags are currently part of the editor's supported original-release profile, not independently proved arbitrary runtime-controlled flags.

Investigations needed before allowing topology editing are maintained only on [Further Investigations](Further%20Investigations.md). Do not infer safe topology editability simply because the lookup table is easy to locate and rewrite.

## Distinguishing three kinds of topology change

1. **Repositioning the editor's map buttons** changes only the user interface. It has no effect on the original game's logical room IDs or the player's room transitions.
2. **Reassigning logical-to-physical room lookup entries** changes which existing physical room appears at a particular logical slot (for Levels 1–3), but does **not** change the `±1/±8` transition calculation. Linked data (START, portals, etc.) may need coordinated changes.
3. **Changing playable topology** (e.g., activating currently unused slots, adding rows, preventing out-of-grid transitions, or connecting nonadjacent rooms) requires additional runtime work and may require expanded storage. This is not proven safe simply because the lookup table is writable.

The HTML5 left panel is arranged to allow future topology tools, but it does not currently perform any of these game-data mutations. See the central [Further Investigations](Further%20Investigations.md) register for the required original-code checks.
