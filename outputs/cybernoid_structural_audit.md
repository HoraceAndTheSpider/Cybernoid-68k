# Cybernoid Amiga structural audit

Verified against repository `data/GAME` on 4 September 2026.

## Lossless round trip

The current `tools/cybernoid_project.py` fixed-size write model was reproduced against
the repository GAME image. Rewriting every field represented by the project model left
the complete **383,230-byte file byte-for-byte identical**. No mismatch was found.

This clears the principal prerequisite for building the editor on top of the structured
project rather than editing GAME directly.

## Logical / physical room model

- 150 physical 20x11 gameplay rooms are represented.
- Level 1 active logical mappings are a one-to-one permutation of physical rooms 0..14.
- Level 2 active logical mappings are a one-to-one permutation of physical rooms 0..22.
- Level 3 active logical mappings are a one-to-one permutation of physical rooms 0..31.
- Level 4 is direct logical == physical for rooms 0..79.
- All inactive Level 1/2 lookup words are literal `$0000`, not invalid-room sentinels.

The zero word at runtime `$40848` and the eleven Level-1 row-padding words remain raw
preserved data rather than room cells.

## START and level-end pads

All four configured start rooms contain exactly one `$02B START` marker:

| Level | Start logical | Physical | START tile |
| --- | ---: | ---: | --- |
| 1 | 0 | 0 | (5,7) |
| 2 | 3 | 0 | (14,4) |
| 3 | 1 | 0 | (16,6) |
| 4 | 9 | 9 | (16,3) |

All four landing pads are valid adjacent `$324/$325` pairs:

| Level | Logical room | Pair |
| --- | ---: | --- |
| 1 | 11 | (15,5) / (16,5) |
| 2 | 24 | (6,5) / (7,5) |
| 3 | 27 | (2,5) / (3,5) |
| 4 | 65 | (9,5) / (10,5) |

## Level-4 portals

There are exactly eight `$1D5` markers and eight 12-byte portal records. Every record
matches its source marker using the now-exact conversion:

```text
trigger_x = tile_x * 16 + 32
trigger_y = tile_y * 16 + 24
```

This conversion is also the general tile-to-game-pixel conversion returned by the
helper at runtime `$10C6A` from the room-build counters `$3FE1C/$3FE1E`.

## ST / ED automatic edge spawning

The 40 automatic-spawn rooms use only one spawn side per room and all markers lie on
the correct corresponding border.

The marker handlers at `$10EB4-$1101F` write persistent endpoint globals:

- `$3FF2E/$3FF30`: first endpoint;
- `$3FF32/$3FF34`: second endpoint;
- `$3FBE8`: side code (`0` bottom, `1` top, `2` right, `3` left);
- `$3FBEA`: spawn-enable flag.

The tile-to-pixel helper adds the appropriate 16-pixel displacement outside the room
edge before storing these coordinates. Importantly, room rebuild clears/rebuilds the
enable state but the four endpoint words are not cleared in the paths found.

Therefore ST/ED is **not safe to normalise into a mandatory conventional pair**.
Two original rooms deliberately or accidentally depend on this persistence:

- Level 3 logical room 23 / physical 26: two `$1E3 ED DOWN` markers, no `$1E2`.
- Level 4 room 40: one `$1E3 ED DOWN` marker, no `$1E2`.

The pygame editor must preserve these raw configurations. A high-level ST/ED editor
should show the inherited-endpoint behaviour rather than silently adding an ST marker.

## ELE paired movers

All 27 horizontal and 34 vertical pairs match correctly, with no unmatched endpoint.
The room loader allocates from slots **43..52** and constructs the linked endpoint in
the immediately following `$42`-byte record. One ELE pair therefore consumes two
adjacent records.

- hard capacity: **5 ELE pairs**;
- maximum in the original rooms: **4 pairs**;
- allocator exhaustion is not guarded before the linked record is constructed.

A high-level editor must reject a sixth pair rather than allowing it to spill into a
neighbouring runtime object band.

## RNET / CRP runtime-capacity correction

Source-marker count is not the same thing as runtime live-object capacity.

### RNET

The four RNET marker handlers allocate primary objects from slots **34..41** through
the generic free-slot allocator at `$153FE`. The caller checks the allocator's failure
condition and skips creation when all eight slots are occupied.

Thus:

- live RNET primary capacity: **8**;
- source rooms may legally contain more than eight markers;
- current maximum source count: **15** in Level 4 room 20;
- later markers can be present in source data but not instantiate when the pool is full.

Original rooms above the live cap are L4 rooms 20 (15), 64 (10), and 70 (9).

### CRP

CRP marker handlers allocate from slots **70..75**, also through `$153FE`, but unlike
RNET the caller does **not** test allocator failure before initialising the returned
record. Original maps already contain rooms with more than six CRP markers, including
26 in Level 4 room 62.

Original rooms above the nominal six-slot band are:

- L2 R11: 8
- L2 R12: 7
- L4 R11: 8
- L4 R27: 7
- L4 R33: 8
- L4 R62: 26
- L4 R72: 8

This is an original engine/data quirk. CRP should initially be **raw/move-only** in the
safe editor layer; arbitrary Add CRP operations should not be exposed until the exact
overflow consequence is deliberately modelled.

## Automatic-enemy and projectile pools

The allocator at `$153FE` works on `$42`-byte records in the main object array.
The automatic edge-spawn routine allocates from slots **54..68** (15 records).

The enemy projectile creation routine at `$16F34` calls the alternate-base allocator
with relative indices 42..50. That alternate base is exactly 77 records after the main
array base, resolving to absolute slots **119..127** (9 projectile records).

## Automatic-enemy script bytecode

The 16 scripts at `$40217-$40401` now decode completely; no unknown opcode occurs in
the current library. `$3FCFC-$3FD3B` remains the 16-longword pointer table in order
BOTTOM 0-3, TOP 0-3, RIGHT 0-3, LEFT 0-3.

Each stream begins with:

```text
byte 0  live object count (1 or 2)
byte 1  animation start
byte 2  animation end
```

The controller/interpreter at `$1BC94` supports:

| Encoding | Meaning |
| --- | --- |
| `$81` | loop back to the post-header command start |
| `$82` | create one enemy projectile |
| `$85` | create three enemy projectiles |
| `$80 nn dx dy` | repeat signed movement `(dx,dy)` for the stored count; `nn=$84` uses `random & $3F` |
| `$83 nn` | stationary wait; `nn=$84` uses `random & $1F` |
| `dx dy` | otherwise, one signed movement pair |

`$82` calls the projectile creator once and `$85` calls the same routine three times.
The raw bytes remain authoritative in the project; the decoded form is an additional
semantic layer only.

See `cybernoid_enemy_scripts_decoded.csv` for all 157 decoded commands.

## Compound destructible validation

All currently mapped canonical compound structures validate successfully:

- `$300` organic cannon anchors: **34 / 34 valid**;
- `$30C` cannon anchors: **25 / 25 valid**;
- `$242` 2x2 anchors: **12 / 12 valid**;
- `$232` 2x3 anchors: **25 / 25 valid**.

The allowed `$300` final-cell `$210` variant remains accepted.

## Remaining unresolved items

1. The four Level-4 anomalous words remain raw and unresolved; their low-byte-only
   candidates are not applied automatically.
2. The exact consequence of CRP allocator exhaustion should be traced before exposing
   arbitrary high-level CRP creation.
3. RNET linked secondary visuals can be investigated further if the editor later needs
   to visualise exact runtime occupancy, although the eight-primary cap is now proven.
4. A per-level palette assignment has not been proven, so the editor exposes palette
   A/B as a display toggle rather than guessing.

These items no longer block a first pygame room editor or fixed-size repacking.
