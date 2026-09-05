# 6. Runtime object pools and capacity

## Why source markers and live objects are not the same thing

A room can contain many enemy/control markers, but the engine has a fixed object array. When the room loads it tries to turn some markers into live object records.

If a relevant pool is full, different families behave differently:

- some callers check failure and skip the new object;
- some callers do not check failure and reuse/overwrite the record just beyond the requested range.

This is why a level editor needs more than a count of map markers.

## Main object record format

The main runtime object records are `$42` bytes each.

A reset routine clears exactly 213 records, slots `0..212`.

Known/important slot bands include:

| Slots | Current interpretation |
|---:|---|
| 0–11 | auxiliary/linked visuals, including RNET companions |
| 13–14 | landing pad halves |
| 15 | player |
| 17 | Back Fire |
| 18 | player projectile |
| 19–32 | generic pickups |
| 31–33 | Cybermace orbiters (overlaps upper pickup band) |
| 34–41 | RNET primaries |
| 43–52 | ELE paired mover records |
| 54–68 | automatic edge enemies / pit homing hostile |
| 70–75 | CRP dedicated crawler slots |
| 76 | CRP overflow record in overloaded rooms |
| 96–117 | `$09F` effects/particles |
| 119–127 | enemy projectiles |
| 129–155 | player special-weapon objects |
| 157–212 | generic room controllers |

## RNET behaviour

RNET primary markers request slots 34–41.

**Verified:** allocator failure is checked. Therefore only the first eight RNET source markers encountered during the room's row-major load order create live primaries. Later RNET markers remain present in the source map but are skipped.

When a primary later locks onto the player it creates a linked companion from slots 0–11.

The editor overlay therefore distinguishes:

- `LIVE` — marker creates a primary;
- `SKIP` — marker is present but the primary pool is already full.

## CRP crawler overflow

CRP markers request slots 70–75, but the caller does not check allocator failure.

The allocator returns the record immediately after the requested range when no free slot remains. For CRP that is slot 76.

Result:

- first 6 CRP markers -> slots 70–75;
- 7th marker -> slot 76;
- 8th, 9th, etc. -> repeatedly overwrite slot 76 during room loading.

Therefore a room containing 26 CRP source markers does **not** have 26 simultaneous crawler records. It has at most seven live crawler records, with the final excess marker determining the final state of slot 76.

This is an original game behaviour, not an editor-created error.

## ELE capacity

ELE uses slots 43–52 in adjacent two-record pairs.

That gives a hard capacity of five pairs per room.

The original maps peak at four pairs. More than five is unsafe because the creation path does not safely handle exhaustion before creating the linked second record.

## Generic controller bank

Many room mechanisms use one record from slots 157–212.

Capacity: **56 records**.

Examples include:

- `$09F` particle emitters;
- portal controllers;
- RACT animations;
- pits;
- `$232/$242/$300/$30C` anchors;
- fixed cannons/guns;
- `$24D` animated pairs;
- every source cell in the `$253-$26E` animation families.

This last point explains why rooms with many energy-field cells consume large numbers of controller records.

The heaviest original room found is:

```text
Level 4 room 77: 52 / 56 controllers used
```

So a semantic “Add Entity” operation should always show/check the room's controller budget.

## Automatic edge-enemy pool

Automatic edge-spawn enemies use slots 54–68: 15 records.

Enemy projectiles use slots 119–127: 9 records.

The 16 movement/script patterns used by the automatic edge system are documented separately in [Automatic enemy scripts](07-automatic-enemy-scripts.md).
