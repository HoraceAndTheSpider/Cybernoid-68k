# 2. Binary layout and addresses

## Plain-language view

`GAME` is not an Amiga HUNK executable. It is a raw, self-relocating 68000 binary.

That means an address seen in the running game is not the same number as the byte position inside the file. For the relocated payload used by the current analysis:

```text
runtime address = file offset + $EE06
file offset     = runtime address - $EE06
```

The extractor works in runtime addresses because that is how the 68000 code refers to the data.

## File size and envelope

**Verified:** `GAME` size is 383,230 bytes (`$5D8FE`).

The relocated payload begins at file offset `$007C`. The six bytes at file offsets `$5D8F8-$5D8FD` are zero and are preserved verbatim. They are treated as part of the file envelope rather than silently folded into the runtime mapping.

## Important fixed blocks

| Purpose | Runtime address | Size / format |
|---|---:|---|
| completion/sequel preview picture | `$1DA90-$1F9CF` | 8000 bytes, 160x100, 4 planes |
| completion preview palette | `$1F9D0-$1F9EF` | 16 Amiga colour words |
| main 16x16 tile bank | `$1FBE8-$3DC67` | 961 tiles, `$80` bytes each |
| automatic-enemy script pointers | `$3FCFC-$3FD3B` | 16 longwords |
| L1-3 level descriptor pairs | `$3FD4E-$3FD65` | three `(lookup,map)` longword pairs |
| L1 lookup allocation | `$3FD66-$3FD95` | 24 words |
| L2 lookup allocation | `$3FD96-$3FDD5` | 32 words |
| L3 lookup allocation | `$3FDD6-$3FE15` | 32 words |
| gameplay HUD/header strip | `$3FF4E-$3FF9D` | 20x2 words |
| start-room IDs | `$3FFB8-$3FFBF` | four words |
| row-stride table | `$3FFC0-$3FFCF` | four longwords |
| Palette A | `$3FFD0-$3FFEF` | 16 colour words |
| Palette B | `$3FFF0-$4000F` | 16 colour words |
| enemy script bytes | `$40217-$40401` | 16 variable streams |
| front-end text/state data | roughly `$40402-$40847` | menu/high-score/name-entry scripts and strings |
| L1 room bank | `$4084A-$42227` | interleaved 20x11 rooms |
| L2 room bank | `$42228-$449AF` | interleaved 20x11 rooms |
| L3 room bank | `$449B0-$480AF` | interleaved 20x11 rooms |
| L4 room bank | `$480B0-$50A2F` | direct 8-wide room grid |
| four post-level layouts | `$50A30-$50F2F` | four 20x8 layouts |
| front-end faux room | `$50F30-$5110F` | 20x12 words |

## A note on “BSS/workspace”

The tile bank ends at `$3DC68`. Some addresses immediately after it are used as runtime workspace/blitter memory rather than source tile data. This was an important distinction during the investigation: not every interesting-looking block beside the graphics is another stored room.

## Why the project keeps addresses in the documentation

Even if someone does not need them for normal editor use, addresses are important because they let another researcher:

- reproduce the extraction independently;
- compare another release/version;
- follow the exact 68000 code path;
- identify whether a field can be expanded or must remain fixed-size;
- eventually re-source the data into assembly labels.
