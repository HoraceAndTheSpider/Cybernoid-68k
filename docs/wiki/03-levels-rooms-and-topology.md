# 3. Levels, rooms and topology

## Room size

Every gameplay room is **20 tiles wide by 11 tiles high**.

Each map square stores one big-endian 16-bit word. Usually that word is a tile ID, but some values are special control markers.

The old 20x12 interpretation was wrong and should not be used for gameplay rooms.

## How many rooms are there?

**Verified:** 150 physical gameplay rooms.

| Level | Physical rooms | Logical room slots |
|---|---:|---:|
| 1 | 15 | 24 allocated (3 rows x 8) |
| 2 | 23 | 32 allocated (4 rows x 8) |
| 3 | 32 | 32 allocated (4 rows x 8) |
| 4 | 80 | 80 direct (10 rows x 8) |

The logical and physical room numbers are deliberately separate for Levels 1–3.

### Why this matters

The player moves through **logical room numbers**. A lookup table converts the logical number to the physical room data that should be loaded.

Level 2 is a useful example: its landing room is logical room 24 even though there are only 23 physical rooms. That alone proves the lookup cannot be treated as a compact `0..22` list.

## Active logical rooms

### Level 1

```text
0  1  2  3  4
8  9 10 11 12
16 17 18 19 20
```

The unused allocated slots contain real `$0000` lookup words, not “invalid room” sentinels.

### Level 2

```text
0  1  2  3  4  5
8  9 10 11 12 13
16 17 18 19 20 21
24 25 26 27 28
```

Again, inactive slots contain real zero lookup words.

### Level 3

All logical slots 0–31 are active.

### Level 4

All logical slots 0–79 are active and logical room equals physical room.

## Room packing on disk

Levels 1–3 are not stored as 15/23/32 complete room blocks one after another. Instead, each *tile row* for all physical rooms is grouped together.

For Levels 1–3:

```text
address = map_base
        + physical_room * $28
        + tile_y * source_row_stride
        + tile_x * 2
```

`$28` is 20 words = one 20-tile source row.

| Level | map base | source row stride |
|---|---:|---:|
| 1 | `$4084A` | `$25A` |
| 2 | `$42228` | `$398` |
| 3 | `$449B0` | `$500` |

Level 1 has one extra padding word after the 15 physical room rows on each of the 11 tile rows.

Level 4 is arranged directly as an 8-room-wide grid:

```text
address = $480B0
        + (room >> 3) * $DC0
        + (room & 7) * $28
        + tile_y * $140
        + tile_x * 2
```

## Moving between rooms

The normal exits modify the logical room number by fixed amounts:

- right: `+1`
- left: `-1`
- up: `-8`
- down: `+8`

The game also remembers the previous room and rejects an immediate transition back into it. This is why topology validation matters: opening a room edge into an inactive logical slot can load an unexpected physical room instead of safely failing.

## Start rooms

The configured logical start rooms are:

```text
Level 1 = 0
Level 2 = 3
Level 3 = 1
Level 4 = 9
```

Each level also contains one `$02B` START marker. The editor checks that the marker and start-room table remain consistent.
