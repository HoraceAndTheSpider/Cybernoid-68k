# Cybernoid semantic entity model

Updated: 5 September 2026

This document defines the high-level entities that can be built on top of the lossless
20x11 raw room maps. Raw source words remain authoritative. The entity layer is a
derived editing/view model and must never silently normalise original data.

## Generic controller budget

The common controller constructor allocates from object slots **157..212**, exactly 56
records. A 57th request reaches slot 213 beyond the cleared object array.

Every occurrence of the following source controls costs one generic controller:

- `$09F`, `$1D5`, `$1E0/$1E1`;
- `$200/$2E2` (plus engine-supported but unused aliases `$2E6/$2EE`);
- anchors `$232`, `$242`, `$24D`, `$300`, `$30C`, `$31C`, `$329`, `$346`;
- every source cell in `$253-$26E`.

The original maximum is **52/56** in Level 4 room 77, leaving four free records.
High-level Add Entity operations must therefore budget controller cost before modifying
a room.

## Atomic animated entities

### `$24D/$24E`: two-cell animation

`$24D` is the only controller anchor. It owns the cell immediately to its right, which
must be `$24E`. The runtime cycles the two displayed cells through five phases:

```text
24D 24E
24F 250
251 252
24F 250
24D 24E
```

All five original `$24D` anchors have the required `$24E` neighbour; `$24F-$252` do not
occur as source-map cells in this GAME. The editor should move/place/delete the pair
atomically. Cost: one generic controller.

### Independent four-frame animation cells

Each source cell is one entity and one controller. Its source word also selects the
initial phase.

| Source family | Cycle | Collision model |
| --- | --- | --- |
| `$253-$256` | descending, wraps | solid |
| `$257-$25A` | ascending, wraps | passable L1-3; live collision `$1234` in L4 |
| `$25B-$25E` | ascending, wraps | passable L1-3; live collision `$1234` in L4 |
| `$25F-$262` | ascending, wraps | solid |
| `$263-$266` | ascending, wraps | solid |
| `$267-$26A` | ascending, wraps | solid |
| `$26B-$26E` | ascending, wraps | solid |

The `$257-$25E` families are therefore the Level-4 energy-field behaviour, even though
the same source values are passable in the earlier levels.

### RACT `$1E0/$1E1`

Each marker is one independent controller:

- `$1E0` cycles runtime display frames `$308-$30B`;
- `$1E1` cycles runtime display frames `$304-$307`.

These are not paired with each other.

## Compound structures

Only the owned/identifying cells belong to the high-level entity. Destruction-side
collateral is a separate concept.

### `$232` 2x3

```text
232 233
234 235
236 237
```

One `$232` anchor, one generic controller.

### `$242` 2x2

```text
242 243
244 245
```

One `$242` anchor, one generic controller.

### `$300` organic cannon

Anchor-relative owned footprint:

```text
    300
    066
062 064 063 065
05C 05D 05E 05F
```

The final `$05F` cell has one proven original variant `$210`. The entity owns ten
cells and consumes one generic controller.

### `$30C` large destructible cannon

Anchor `$30C` sits in an 11-owned-cell structure:

```text
116 117 118 119
11A 30C 30D 11D
11E 30E 30F xxx
```

`xxx` is **not owned by the cannon**. Original values there are `$121`, `$049`, `$04A`,
`$04B` and `$003`. Runtime destruction can affect that context/collateral position,
but semantic move/delete must leave it in place.

## Single-cell controller entities

The following are structurally one source cell plus one generic controller:

- `$09F` particle emitter. Runtime child allocation uses shared slots 19..40 and checks
  failure, so adding one is memory-safe but may reduce/suppress transient output when
  that pool is busy.
- `$200/$2E2` Level-4 mixed spawn pit. The controller chooses cargo or a homing hostile.
  Cargo and hostile creation paths both guard child-pool exhaustion. `$2E6/$2EE` are
  dispatcher aliases with zero current map occurrences.
- `$31C`, `$329`, `$346` firing controllers. Their projectile creation paths guard
  projectile-pool exhaustion.

## ELE paired movers

The current maps contain 27 horizontal and 34 vertical pairs with no unmatched
endpoint. One pair consumes two adjacent runtime object records from slots 43..52.
Hard capacity: **five pairs per room**.

Safe high-level editing can create/move/delete a complete pair, provided the resulting
room remains at or below five pairs. The canonical source forms are:

- horizontal: `$1F6` start with `$1F7` to its right on the same row;
- vertical: `$1F8` start with `$1F9` below it in the same column.

## Portals

There are exactly eight 12-byte records at `$1659E` and eight `$1D5` source markers.
The runtime loop is hard-coded for eight records, so the fixed-size editor should not
Add/Delete portal records.

The record is best edited in tile coordinates:

```text
pixel_x = tile_x * 16 + 32
pixel_y = tile_y * 16 + 24
```

This conversion holds for both current source triggers and all current destination
coordinates. The safe entity UI should expose source room/tile and destination
room/tile, then regenerate stored pixel values.

Important correction: **multiple portals may share one Level-4 source room**. Runtime
matches `(room, trigger coordinates)` for each record. Only duplicate records at the
same room and same trigger are invalid/unreachable by table order.

## START and landing pad

- Exactly one `$02B START` per level; moving it must also update that level's logical
  start-room table entry.
- Exactly one `$324/$325` adjacent landing-pad pair per level; move as a two-cell pair.

These are fixed-count structures in the safe editor rather than arbitrary Add/Delete.

## RNET runtime presentation

RNET source markers are scanned in room row-major order. Primaries allocate slots
34..41 and allocation failure is checked.

- source markers 1..8: `live_primary`;
- source markers 9+: `skipped_pool_full` on that room load.

The original over-cap rooms are L4 R20 (15), R64 (10) and R70 (9). Moving or inserting
an RNET marker can therefore change which later source markers instantiate. A safe Add
operation should initially be limited to rooms with fewer than eight RNET markers.

RNET linked companions later allocate from slots 0..11. Those explicit 0..11 requests
are RNET behaviours, although broader transient 0..75 allocator paths also exist, so
the editor should continue to show an auxiliary-pool warning rather than claim the
companion pool is exclusive.

## CRP runtime presentation

CRP source markers are also processed row-major:

- first six -> slots 70..75 (`dedicated_live`);
- seventh and every later marker -> allocator failure returns slot 76, which the caller
  still initialises;
- each later excess marker overwrites slot 76 again;
- after room build, only the **last** excess marker remains represented in slot 76.

Thus over-cap rooms collapse to at most seven live crawler records. The semantic UI can
show exact roles:

- `dedicated_live`;
- `overflow_overwritten`;
- `overflow_slot76_live`.

The original over-cap rooms must remain legal. New Add CRP should initially be limited
to a resulting count of six or fewer; moving/deleting original excess markers is
allowed but must recompute and display the row-major roles.

## ST / ED edge-spawn bands

ST/ED markers define one side-band configuration, but the endpoint globals persist
between room rebuilds. Original ED-only configurations exist and must not be repaired
into conventional pairs. Treat the whole side-band as an advanced entity for display,
while retaining individual raw markers and cardinality.

## Safe first high-level editor policy

**Atomic Add/Move/Delete:** `$24D/$24E`, `$253-$26E`, RACT, `$232`, `$242`, `$300`,
`$30C`, `$31C`, `$329`, `$346`, `$09F`, L4 `$200/$2E2`, ELE pairs (<=5).

**Fixed-count Move/Re-target only:** portals, START, landing pad.

**Runtime-constrained:** RNET and CRP. Show exact load roles; only permit additions
within the conservative 8/6 source-marker limits initially.

**Advanced/raw-preserving:** ST/ED, unresolved anomalous source words, unusual aliases.

## Tested semantic mutation layer

`tools/cybernoid_entity_ops.py` now implements the proven edit rules as transactional
backend operations. These are deliberately separate from pygame interaction so the
binary invariants can be tested without relying on drag/drop behaviour.

Current operations include:

- move/re-target one of the eight portal records while synchronising its `$1D5` marker;
- move START while synchronising the per-level logical start-room table;
- move the fixed `$324/$325` landing pair;
- add/move/delete complete ELE pairs, rejecting a sixth pair;
- add/move/delete `$232`, `$242`, `$300` and `$30C` compounds;
- `$30C` move/delete explicitly preserves its non-owned `(+2,+1)` collateral/context cell;
- add/move/delete `$24D/$24E` as one two-cell entity;
- add/move/delete approved independent one-cell controller entities with the 56-record
  controller budget enforced;
- conservative RNET/CRP Add operations (8/6 source caps), plus move/delete operations
  that return before/after row-major runtime-role assignments.

Vacated cells default to source tile `$000`, which is both visually blank and explicitly
listed as passable by the game's passability table. The API accepts a different clear
value so a future UI can let the editor choose what underlying/background tile should
replace a moved or deleted entity.

The mutation tests are in `tools/test_cybernoid_entity_ops.py`. They currently cover
portal synchronisation including two portals sharing one source room, START and landing
movement, `$30C` collateral preservation, ELE capacity, the 56-controller ceiling and
RNET/CRP conservative Add caps.
