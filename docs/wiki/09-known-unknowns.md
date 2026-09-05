# 9. Known unknowns and current research status

This page records areas that are deliberately **not** presented as solved.

## Four anomalous Level-4 room words

Four Level-4 source words are outside the normal `0..960` tile range:

| Room | Cell | Runtime | File | Raw word | low-byte candidate |
|---|---|---:|---:|---:|---:|
| 40 | (2,10) | `$4D1F4` | `$3E3EE` | `$086F` | `$006F` |
| 44 | (5,8) | `$4D01A` | `$3E214` | `$B087` | `$0087` |
| 44 | (6,8) | `$4D01C` | `$3E216` | `$8D26` | `$0026` |
| 47 | (18,9) | `$4D1EC` | `$3E3E6` | `$0F4B` | `$004B` |

All four lie in the same aligned 512-byte file block `$3E200-$3E3FF`.

The impossible-looking part is entirely in the high byte, which makes isolated high-byte corruption a plausible explanation. However, the project **does not automatically patch them**.

Additional evidence:

- `$006F`, `$0026` and `$004B` are common normal gameplay tiles;
- `$0087` occurs nowhere else in gameplay rooms, but it is a valid blank/solid tile and could plausibly be an intentional invisible collision tile.

Best future resolution: compare against another trusted copy of the **same release/edition**.

## Release/version differences

The WHDLoad installer supports more than one Cybernoid release, and known Action Amiga/original-release graphics differences exist.

Therefore future tooling should identify the source binary using hash/size/profile rather than assuming every Cybernoid `GAME` has identical data at the same offsets.

## RNET auxiliary pool sharing

RNET companions explicitly request slots 0–11, but other broader transient allocators can also touch low object slots. The current editor therefore treats RNET creation conservatively even though primary behaviour is well understood.

## ST/ED inherited endpoint behaviour

The endpoint globals used by automatic edge spawning are not cleared in the same way as the room enable flag. This explains why ED-only rooms can have meaningful behaviour based on previously held endpoint values.

The behaviour is understood enough to preserve original layouts, but a friendly high-level ST/ED editor still needs careful design because changing one room may affect what is inherited when arriving from another room.

## Full source/recompile status

The game-data model is much further advanced than a full reassemblable source.

A complete re-source would still need:

- broad code labelling and reassembly verification;
- full loaded-image vs BSS/workspace memory map;
- relocation strategy for expanded data;
- confidence across release variants;
- build output comparison against the original binary.

For the current fixed-size level editor, none of that is a blocker.

## Current practical status

### Solved enough for fixed-size editing

- all 150 gameplay rooms;
- logical room topology;
- tile bank;
- gameplay/menu/Level-4 palette model;
- front-end 20x12 faux room;
- post-level layouts;
- portal table;
- START/landing-pad relationships;
- ELE pairing;
- major compound entities;
- generic controller capacity;
- RNET and CRP source-vs-runtime roles;
- automatic enemy script bytecode;
- byte-identical no-edit repacking.

### Still intentionally conservative in the UI

- arbitrary RNET/CRP creation;
- ST/ED high-level editing;
- enemy-script resizing;
- adding new rooms/portal records/tiles;
- relocation/growth;
- automatic repair of the four anomalous Level-4 words.
