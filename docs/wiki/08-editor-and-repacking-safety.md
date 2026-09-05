# 8. Editor and repacking safety

## What Save and Export mean

The pygame editor works on an extracted project rather than directly editing `data/GAME`.

### Save

`Save` writes the current structured `project.json`.

It does **not** overwrite the original source `GAME`.

### Export

`Export` first runs the structural checks. If there are blocking errors it stops and identifies the first problem by level/room/cell where possible.

If the checks pass, it creates `GAME.patched` (or the path supplied with `--output`).

## Why Export can be blocked

The audit is there to stop edits that would produce internally inconsistent game data.

Examples of blocking conditions include:

- missing or duplicate START relationships;
- broken landing-pad pair;
- portal record no longer matching its `$1D5` trigger;
- unmatched ELE endpoint;
- compound object missing one of its owned cells;
- too many generic controllers in one room;
- known unresolved anomaly changed accidentally.

Warnings/information do not necessarily block export.

## Original oddities are not automatically errors

A key project rule is:

> unusual original data is not the same as invalid data.

Examples already accounted for include:

- ED-only automatic spawn arrangements;
- BOTTOM ST/ED markers on source row 9 in Level 4 rooms 51 and 55;
- CRP rooms containing more source markers than dedicated crawler slots;
- RNET rooms containing more source markers than can become live primaries;
- four unresolved high-byte-looking Level-4 map words.

The audit should model the engine's actual behaviour, not an imagined “clean” data format.

## Raw painting vs semantic editing

### Raw painting

The current editor can place a selected 16-bit tile/control value directly into a room square.

This is powerful but low-level: it is possible to break relationships such as a multi-cell object or portal.

### Semantic editing

The tested backend is being built so that higher-level operations can make the required related changes together.

Examples:

- move a portal trigger and update its table record;
- move both halves of a landing pad together;
- move/delete all owned cells of a `$30C` cannon while preserving its contextual bottom-right neighbour;
- add an ELE pair only when a fifth pair still fits;
- add a controller-using entity only when the room remains at or below 56 controllers.

## Fixed-size limits

The current repacker deliberately rejects relocation/growth.

That means it can safely edit existing fixed-size structures, but cannot yet do things such as:

- add a ninth portal record;
- expand the tile bank beyond 961 tiles;
- add new rooms beyond the existing allocations;
- grow an enemy script past its original allocation;
- relocate major code/data blocks.

Those changes would move the project toward a full re-source/recompile approach.

## Recommended workflow for tool developers

1. Extract from a known source `GAME`.
2. Record source size/hash/version profile.
3. Retain all raw values.
4. Derive semantic objects separately.
5. Validate before export.
6. Repack into a new output file.
7. Compare/retest in emulator or real hardware.
8. Never silently normalise unknown or anomalous source data.
