# Cybernoid Amiga reverse-engineering follow-up

Status: 5 September 2026

This note records the investigations performed after the first pygame editor / semantic-audit commit.

## 1. Generic controller bank is now bounded exactly

The main object reset routine at runtime `$11650` clears exactly 213 records of `$42` bytes, proving that the runtime object array is slots `0..212` inclusive.

The common map-controller constructor at `$114C2` calls helper `$10660`.  That helper searches for the first inactive record beginning at slot 157 (`$6EF30`).  The normal bank is slots **157..212**, exactly **56 records**.  A 57th request reaches slot 213, one record beyond the cleared object array.

This makes **56 generic controllers a hard editor limit**.

The dispatcher paths that consume one record from this bank are:

- `$09F` particle/effect controller;
- `$1D5` Level-4 portal controller;
- `$1E0/$1E1` RACT animation controllers;
- `$200/$2E2` mixed-pit controllers (the binary also has dormant handlers for `$2E6/$2EE`);
- `$232` and `$242` compound-structure anchors;
- `$24D` animated two-cell mechanism anchor;
- `$300`, `$30C`, `$31C`, `$329`, `$346` cannon/emitter anchors;
- animated/control ranges `$253-$256`, `$257-$25E`, `$25F-$262`, `$263-$266`, `$267-$26A`, `$26B-$26E`.

Across the original 150 gameplay rooms, the maximum controller demand is **52 records in Level 4 room 77**, leaving only four spare records.  A high-level editor therefore needs a per-room controller-budget validator whenever it adds one of these entities/tiles.

## 2. CRP overflow behaviour is now exact

CRP markers request slots `70..75` through allocator `$153FE`.  The allocator indicates failure through condition codes, but the CRP caller does not test them.

When all six records are occupied, the allocator has advanced its returned pointer to the record immediately after the requested range: **slot 76 at `$6DA4E`**.  The seventh CRP is therefore initialised into slot 76.

Every later excess CRP repeats the same 70..75 scan and again returns slot 76, so it **overwrites the previous slot-76 crawler rather than spilling onward**.

Slot 76 is included in the normal lower-object update/draw pass.  The effective original behaviour is therefore:

- first six CRP markers -> slots 70..75;
- seventh CRP marker -> slot 76;
- eighth and later markers -> overwrite slot 76;
- maximum simultaneous crawler records produced by this path: seven.

This explains how original rooms can contain 8, 26, etc. CRP source markers without requiring 8/26 dedicated runtime slots.  The raw marker ordering still matters because the last excess marker determines the final state of slot 76.

For the pygame editor, CRP should remain raw/move-only for now.  An eventual high-level CRP editor must make this collapse/overwrite behaviour explicit rather than pretending every source marker becomes a separate live crawler.

## 3. RNET linked companions

RNET primaries are allocated from slots `34..41` and allocator failure is checked, so at most eight primaries instantiate.

When a primary aligns with the player and enters its charging phase, it allocates a linked companion from slots **0..11**.  The companion allocation does **not** test failure before linking the returned record.  Eight RNET companions by themselves fit in the 12-slot auxiliary band, but another broad `0..75` allocator path also exists, so the auxiliary band cannot yet be treated as exclusively reserved for RNET.

Consequently:

- existing RNET source data is safe to preserve;
- moving/changing existing RNET markers is reasonable;
- arbitrary high-level RNET additions should remain conservative until auxiliary-slot sharing is completely bounded.

## 4. Gameplay palette resolved

Palette B at runtime `$3FFF0` is the normal gameplay-room palette source.

The game writes `$3FFF0` to live palette-source pointer `$15086`, calls the palette staging routine at `$165FE`, clears current level `$3FD3C`, then proceeds into level/map setup.  Palette A (`$3FFD0`) is selected in separate setup/transition paths and is not a per-level gameplay palette alternative.

The pygame room editor should therefore default to **Palette B**.  Palette A remains useful as a manual setup/transition reference toggle.

## 5. Level-4 anomaly candidates: stronger differentiation

All four raw anomalies remain unmodified in the lossless project.

The three candidates `$006F`, `$0026`, and `$004B` are normal map tiles used elsewhere 28, 171 and 100 times respectively.

`$0087` is different: it occurs nowhere else in the 150 gameplay rooms, but its tile-bank graphics are completely blank and it is **not** present in the passability table.  It would therefore behave as an invisible solid collision tile.  That is a credible use next to the CRP/platform geometry in Level 4 room 44, so `$B087 -> $0087` remains plausible rather than being rejected simply because `$087` is otherwise unused.

The shared aligned 512-byte block `$3E200-$3E3FF`, together with four otherwise-invalid words whose low bytes all resolve to credible tile IDs, remains strong evidence for isolated high-byte corruption.  The candidates are still not authorised replacements without a second trusted binary.
