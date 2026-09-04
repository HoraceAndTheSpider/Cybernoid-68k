# Cybernoid Amiga editor / repacker status

Updated: 4 September 2026

The project has crossed the main implementation boundary: the fixed-size
`GAME -> structured project -> GAME` model is now verified byte-identically, the
current automatic-enemy script library is semantically decoded, and the first pygame
editor can sit on the same validated project model.

The current priority remains **safe fixed-size editing**, not broad 68000 relabelling or
full recompilation.

## 1. Lossless project / repacker

`tools/cybernoid_project.py` retains an exact source GAME and only scatters known
fixed-size project fields back into it. Reproducing all of those writes against the
repository `data/GAME` leaves the complete 383,230-byte image **byte-for-byte
identical**.

This is the required no-edit round-trip milestone.

Runtime/file mapping for the relocated payload remains:

```text
runtime = file_offset + $EE06
file_offset = runtime - $EE06
```

The six final file bytes `$5D8F8-$5D8FD` are zero and preserved verbatim. Runtime
`$40848` is a separate zero word before the Level-1 map and is also preserved.

## 2. Gameplay maps and topology

Gameplay rooms are 20x11 words.

| Level | Active logical layout | Physical rooms | Lookup | Map base | Source-row stride |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 15 active slots in a 3x8 allocation | 15 | `$3FD66` (24 words) | `$4084A` | `$25A` |
| 2 | 23 active slots in a 4x8 allocation | 23 | `$3FD96` (32 words) | `$42228` | `$398` |
| 3 | 32 active slots, 4x8 | 32 | `$3FDD6` (32 words) | `$449B0` | `$500` |
| 4 | 80 direct slots, 10x8 | 80 | direct | `$480B0` | `$140` |

All active Level 1-3 mappings currently form one-to-one permutations of their physical
room banks. Inactive Level 1/2 lookup entries are literal `$0000`, not invalid-room
sentinels.

Levels 1-3 cell address:

```text
map_base + physical_room * $28 + y * source_row_stride + x * 2
```

Level 4 cell address:

```text
$480B0 + (room >> 3) * $DC0 + (room & 7) * $28 + y * $140 + x * 2
```

## 3. Fixed-size editable blocks

| Data | Runtime address / range |
| --- | --- |
| Completion preview image | `$1DA90-$1F9CF` |
| Completion preview palette | `$1F9D0-$1F9EF` |
| Tile bank, IDs 0-960 | `$1FBE8-$3DC67` |
| Enemy script pointer table | `$3FCFC-$3FD3B` |
| L1-3 level descriptor pairs | `$3FD4E-$3FD65` |
| Start rooms | `$3FFB8-$3FFBF` |
| Source row strides | `$3FFC0-$3FFCF` (4 longwords) |
| Palette A | `$3FFD0-$3FFEF` |
| Palette B | `$3FFF0-$4000F` |
| Automatic-enemy script data | `$40217-$40401` inclusive |
| Level-4 portal table | `$1659E-$165FD` |
| Post-level layouts | `$50A30-$50F2F` |

## 4. Structural audit now proven

- four START markers exactly match the four configured start rooms;
- four valid adjacent `$324/$325` landing-pad pairs;
- eight Level-4 `$1D5` markers exactly match eight portal records;
- portal trigger conversion is exactly `x*16+32`, `y*16+24`;
- 27 horizontal and 34 vertical ELE pairs, no unmatched endpoint;
- 40 automatic edge-spawn rooms, no room uses more than one side;
- all 34 `$300`, 25 `$30C`, 12 `$242`, and 25 `$232` canonical compound structures validate.

Detailed evidence is in `outputs/cybernoid_structural_audit.md`.

## 5. ST / ED persistence: do not normalise

The tile-coordinate helper at `$10C6A` converts current room tile counters to pixels.
The `$1E2-$1E9` handlers then write two global endpoint pairs at `$3FF2E/$30` and
`$3FF32/$34`, plus side code `$3FBE8` and enable state `$3FBEA`.

The endpoint words are not cleared on the room-rebuild path found. This explains why
ST/ED is not safely modelled as a compulsory conventional start/end pair.

Two original rooms are intentionally preserved as non-standard configurations:

- L3 logical R23 / physical 26: two `$1E3 ED DOWN`, no `$1E2`;
- L4 R40: one `$1E3 ED DOWN`, no `$1E2`.

A high-level editor must show endpoint inheritance rather than auto-repair these rooms.

## 6. Runtime object-pool implications

The generic allocator at `$153FE` scans `$42`-byte object records.

### RNET

RNET handlers allocate primaries from slots 34..41 and **check** allocator failure.
Only eight live primaries can instantiate even though source rooms can contain more
markers. Current source maximum is 15 markers in L4 R20.

### ELE

Each ELE pair uses two adjacent records from slots 43..52. The loader does not guard
pool exhaustion before constructing the linked record. Hard safe capacity: **5 pairs**;
current maximum: 4.

### Automatic edge enemies

The spawn routine uses slots 54..68: **15 live records**.

### CRP

CRP handlers use nominal slots 70..75 but do not guard allocator exhaustion. Original
rooms already exceed six markers (up to 26 in L4 R62). Do not infer a simple source
marker limit or normalise these layouts. High-level Add CRP remains disabled for now.

### Enemy projectiles

The projectile routine at `$16F34` resolves to absolute slots 119..127: **9 records**.

## 7. Automatic-enemy script bytecode

All 16 current scripts decode completely. The three-byte header is:

```text
object_count, animation_start, animation_end
```

Current bytecode semantics:

```text
$81             loop to post-header command start
$82             fire one enemy projectile
$85             fire three enemy projectiles
$80 nn dx dy    repeat signed movement; nn=$84 => random & $3F
$83 nn          stationary wait; nn=$84 => random & $1F
dx dy           otherwise one signed movement pair
```

The raw streams remain authoritative. Decoded commands are an overlay only.
See `outputs/cybernoid_enemy_scripts_decoded.csv`.

## 8. Four unresolved Level-4 source words

These remain raw first-class values and are not repaired automatically:

| Room | x,y | Runtime | Raw | Low-byte-only candidate |
| --- | --- | ---: | ---: | ---: |
| 40 | 2,10 | `$4D1F4` | `$086F` | `$006F` |
| 44 | 5,8 | `$4D01A` | `$B087` | `$0087` |
| 44 | 6,8 | `$4D01C` | `$8D26` | `$0026` |
| 47 | 18,9 | `$4D1EC` | `$0F4B` | `$004B` |

They remain clustered inside file block `$3E200-$3E3FF`; a second trusted copy is still
the preferred resolution.

## 9. Pygame editor

The first GUI is `editor/cybernoid_editor.py` and deliberately works on an extracted
project rather than directly on GAME.

Current first-stage features:

- logical 8-wide level-map navigation, including inactive holes;
- real 961-tile planar rendering;
- palette A/B display toggle without guessing a per-level assignment;
- semantic marker overlays;
- raw tile/control painting with undo and eyedropper;
- project save;
- structural validation after edits;
- fixed-size repack blocked if validation contains errors.

High-level Add Entity tools remain disabled until each family has a safe runtime
capacity/editing rule. ELE is now safe enough for a future paired-entity tool; RNET can
be modelled with its eight-live-primary cap; CRP still needs special handling.

## 10. Remaining reverse-engineering priorities

1. Trace the exact CRP exhaustion consequence before exposing arbitrary CRP creation.
2. Resolve the four anomalous Level-4 words against another trusted image if possible.
3. Optionally derive a proven palette/level association rather than retaining manual A/B
   display selection.
4. Add higher-level pygame operations family-by-family, beginning with portal syncing,
   START syncing, ELE pair creation/movement, and validated compound structures.
5. Only consider relocation/full reassembly when requested edits exceed fixed-size data.
