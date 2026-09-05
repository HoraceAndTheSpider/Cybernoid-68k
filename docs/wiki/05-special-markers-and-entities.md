# 5. Special markers and semantic entities

## The most important concept

A gameplay room square stores **one 16-bit value**.

There is no second hidden “background tile” underneath a special marker.

If a square stores `$1D5` for a portal, `$1D5` is the actual room value at that position. When the room loads, the engine recognises it and creates the appropriate gameplay behaviour.

This is why a safe “move object” operation must know what ordinary tile should replace the object's old location. The editor cannot recover a hidden underlay because none is stored.

## Common special/control markers

| Word | Meaning |
|---:|---|
| `$02B` | player START |
| `$09F` | particle/environment effect emitter |
| `$1D5` | Level-4 portal trigger |
| `$1E0/$1E1` | RACT animation markers |
| `$1E2-$1E9` | automatic edge-enemy ST/ED markers |
| `$1F0/$1F1/$1F4/$1F5` | RNET directional hostile markers |
| `$1F2` | Cybermace bonus |
| `$1F3` | special weapon ammunition bonus |
| `$1F6-$1F9` | ELE paired mover endpoints |
| `$1FA` | Back Fire bonus |
| `$1FC-$1FF` | CRP crawler variants |
| `$200/$2E2` | Level-4 mixed cargo/homing-hostile pit |
| `$300` | organic/plant cannon anchor |
| `$30C` | large destructible cannon anchor |
| `$31C` | fixed cannon |
| `$324/$325` | two halves of landing pad |
| `$329/$346` | right/left guns |

## What is an “entity” in the editor?

An entity is an editor concept: several raw map cells may together represent one object that should be moved or deleted as a unit.

### `$232` family

One 2x3 destructible entity:

```text
232 233
234 235
236 237
```

All six cells belong to the object.

### `$242` family

One 2x2 destructible entity:

```text
242 243
244 245
```

All four cells belong to the object.

### `$300` organic cannon

The anchor is `$300`. The required ten-cell arrangement is:

```text
    300
    066
062 064 063 065
05C 05D 05E 05F
```

One original instance uses `$210` instead of the final `$05F`; that variant is preserved as valid original data.

### `$30C` large destructible cannon

The cannon owns 11 cells:

```text
116 117 118 119
11A 30C 30D 11D
11E 30E 30F ???
```

The final bottom-right `???` cell is **not part of the cannon entity**. In the original maps it varies between values such as `$121`, `$049`, `$003`, `$04A` and `$04B`.

Therefore a semantic move/delete operation must leave that contextual cell alone.

### `$24D/$24E` two-cell animated object

Only `$24D` creates the controller. The source map contains one adjacent pair:

```text
24D 24E
```

The runtime animation cycles through:

```text
24D/24E
24F/250
251/252
24F/250
24D/24E
```

The editor should treat the two source cells as one atomic object.

### `$253-$26E` animation families

These are **not** larger multi-cell mechanisms. Each source map cell creates its own controller and cycles within a four-tile animation family.

The ranges are:

```text
253-256
257-25A
25B-25E
25F-262
263-266
267-26A
26B-26E
```

`$257-$25E` are the energy-field families. In Levels 1–3 they are passable; in Level 4 the room loader replaces the live collision value with `$1234`, making them lethal.


### `$31C` fixed cannon

The source marker is only the controller end of a two-cell source pair:

```text
31C 31D
```

Every original `$31C` placement contains the adjacent `$31D`. The runtime then animates the pair through `$31E/$31F`, `$320/$321` and `$322/$323` frames.

### `$329` right-facing gun

The visible/controller tip `$329` is the right-most cell of a four-cell source strip:

```text
326 327 328 329
```

Every original `$329` placement has all four cells. Multiple `$329` guns are legal in the original game, but they share one global firing timer at `$3FF2C`, so the projectile and firing animation can occur on different mounts.

### `$346` left-facing gun

The mirror source strip is:

```text
346 347 348 349
```

One original instance uses `$359` for the last cell and is preserved as a valid variant. All `$346` guns share global firing timer `$3FF2A`; the original maps contain as many as five in one room.

The editor therefore treats these guns as compound placements and warns about the shared-timer behaviour instead of limiting them to one.

## ELE paired movers

The source uses endpoint pairs:

- `$1F6` start -> `$1F7` end on the same row;
- `$1F8` start -> `$1F9` end in the same column.

The editor should move/add/delete the endpoints as one paired entity.

The runtime object pool allows five simultaneous ELE pairs per room.

## Portals

A portal consists of both:

1. a `$1D5` marker in a Level-4 room; and
2. one 12-byte record in the eight-entry portal table at `$1659E`.

Each record stores:

```text
source room
source trigger X
source trigger Y
destination room
destination X
destination Y
```

Both source and destination pixel coordinates map exactly to the editor's tile grid:

```text
pixel X = tile X * 16 + 32
pixel Y = tile Y * 16 + 24
```

The engine matches by **source room plus trigger coordinates**, not source room alone. Multiple portals could therefore share one room if their trigger squares differ, even though the original eight portals use distinct source rooms.

The current fixed-size game has eight portal records, so the safe editor model is to move/re-target those eight rather than silently create a ninth record.

## ST/ED automatic-edge markers

These describe automatic enemy-entry bounds on one room side. The original editor-like names appear to be “Start” and “End”, but the runtime coordinate arithmetic is not always a conventional ordered pair.

Important original quirks:

- Level 3 room 23 has two ED DOWN markers and no ST DOWN;
- Level 4 room 40 has an ED DOWN marker without ST DOWN;
- Level 4 rooms 51 and 55 place DOWN markers on source row 9 rather than row 10.

The endpoint globals can persist between room builds. Therefore the current editor deliberately preserves these original arrangements instead of normalising them.
