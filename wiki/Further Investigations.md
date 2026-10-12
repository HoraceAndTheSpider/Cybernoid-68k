# Further Investigations — Cybernoid Amiga

**Single register of unresolved questions.** Keep genuine game-engine facts on the permanent subject page; keep this page for open questions, evidence needed and investigation priorities. Do not start parallel investigation pages or repeat completed research. Updated for HTML5 editor v0.2 (12 October 2026).

Confidence terminology: **Verified** = backed by original binary/runtime path or live testing; **Strong inference** = plausible but not completely proved; **Unresolved** = insufficient evidence; preserve source data verbatim.

## Priority 1 — room topology and changeable level maps (Unresolved)

**Already verified:** 20×11 room tiles; 150 physical gameplay rooms; physical counts 15/23/32/80; logical slot allocations 24/32/32/80, eight slots per row; Levels 1–3 have physical lookup tables at `$3FD66`, `$3FD96`, `$3FDD6`. Level 4 uses direct logical/physical mapping. Normal transitions adjust logical room by ±1 or ±8. See [Levels, rooms and topology](03-levels-rooms-and-topology.md).

**Open questions before a user-editable topology map:**

- Which gameplay code decides whether a ship can exit a room on each edge? Are visual/collision edges sufficient, or are there explicit active-slot/boundary tests?
- Which conditions gate a transition into a slot currently marked inactive? The original inactive lookup entries are real zero words, not sentinel values.
- Does the engine assume a fixed width of eight logical slots, and are row counts/counters and map traversal constants hard-coded?
- Is it safe to *remap* an existing active logical slot to a different physical room without adjusting other linked data, including room start locations, portal transitions and special events?
- Can an allocated-but-inactive slot become safely active without data relocation, and what visible display/navigation effects result?
- Which additional changes would be needed to change the actual number or arrangement of physical room allocations? This is beyond fixed-size repacking.

**Next evidence:** trace the room-exit and lookup code, document runtime entry points and conditions, then test a deliberately minimal lookup remapping on a **disposable copy of GAME**, recording its exact before/after lookup and all START/portal relationships. Until proved, the HTML5 left-hand room grid is **read-only topology** and does not expose remapping or slot activation.

## Priority 2 — HTML5 feature parity and edit/export validation (In progress)

- Port the remaining semantic checks from `tools/cybernoid_semantics.py` and `tools/cybernoid_entity_ops.py`. First HTML5 release checks core invariants only; it must not claim complete Python audit parity.
- Implement atomic move/add/delete for supported special entities, preserving the verified owner/underlay rules. Do not add a ninth portal record without relocation research.
- Investigate the highest-priority non-destructive editing workflow for START, landing, cannon and ELE pairs before enabling their manipulation.
- Validate the browser import and source-preserving export on the owner's actual original GAME; local first-pass synthetic-binary testing is not equivalent to live hardware testing.

## Priority 3 — tile/palette authoring (Planned)

- Implement a 16×16 indexed pixel tile editor with palette operations, brushes, Undo/Redo, and exported bitplanes. Base drawing geometry can borrow resource-neutral routines from the Indy Heat editor.
- Define safe operations on the 961 existing tile IDs versus speculative extra tiles. Current bank is a fixed `$80`-byte record ×961, with fixed-size repacker restrictions.
- Check tile usage and animation families before providing destructive graphics edits; tiles used by source control sequences may have relationships not apparent from their appearance.
- Add editing for Palette A, Palette B and the Level-4 `$1CD10` eight-word override, with awareness of the `$1CD30` Palette B restore table.
- Consider whether front-end faux-room/HUD editing should be separate screens/modes rather than ordinary gameplay rooms.

## Known binary anomalies (Unresolved; unchanged)

Four Level-4 source words lie outside the tile bank range `0..960`; all four are in the same aligned 512-byte file block `$3E200–$3E3FF`:

| Level 4 physical room | Tile (x,y) | Runtime address | File offset | Raw 16-bit word | Possible low-byte interpretation |
|---|---|---|---|---|---|
| 40 | (2,10) | `$4D1F4` | `$3E3EE` | `$086F` | `$006F` |
| 44 | (5,8) | `$4D01A` | `$3E214` | `$B087` | `$0087` |
| 44 | (6,8) | `$4D01C` | `$3E216` | `$8D26` | `$0026` |
| 47 | (18,9) | `$4D1EC` | `$3E3E6` | `$0F4B` | `$004B` |

**Strong inference**, not proven: isolated high-byte corruption could explain all four. Values `$006F`, `$0026` and `$004B` occur elsewhere as ordinary tiles. `$0087` is otherwise absent from gameplay but is a valid blank/solid tile. **Do not repair, convert or normalise these values automatically.**

**Next evidence:** locate and compare a trusted second copy of the **same release/edition**; record edition identity and hashes before comparing.

## Game editions / source profiles (Unresolved)

The installer supports multiple releases, and Action Amiga/original-release graphics differ. Source selection should eventually rely on release-specific signatures (hash/size/descriptor profile), with separate layout profiles rather than treating every binary as identical. Current HTML5 loader deliberately refuses a file with a different size, descriptor or stride profile. Find trustworthy binaries and prove profile-to-format differences.

## RNET auxiliary pools (Partially understood)

The first eight RNET primaries are live; later source markers are skipped. Companions explicitly request low object slots 0–11, which broader transient allocators may also reuse. Preserve real runtime ordering and consider additional observations before enabling arbitrary creation. See [Runtime object pools](06-runtime-object-pools.md).

## ST/ED inherited endpoint semantics (Partially understood)

Automatic edge-spawn endpoints are kept in global words that persist across some room builds. Some authentic maps contain ED-only arrangements, and Level 4 uses row 9 in some DOWN cases. Editing a room can therefore affect subsequent rooms through inherited state; no general-purpose ST/ED editor until route-dependent effects are better established. See [Special markers](05-special-markers-and-entities.md).

## Full source/recompile capability (Long term)

Game-data modelling is much further advanced than a complete reassemblable source. Pending work includes broad code labelling/reassembly comparison, loaded-image/BSS/workspace mapping, relocation strategy for expanded data, cross-version confidence and complete binary build verification. **Not required for the current fixed-size editor.**

## Already solved — do not reopen without contradictory evidence

- All 150 physical rooms and their current logical topology.
- The authentic 961-tile 4-bitplane bank, palettes, Level-4 override, and front-end 20×12 faux-room distinction.
- Fixed-size source-preserving round-trip in Python; the HTML5 output currently uses the unchanged extensionless `GAME` filename (WHDLoad integration deliberately deferred).
- START/landing relationship, eight Level-4 portal records, ELE pairing, compound cannon bodies, ordinary collision passability table, generic controller cap, RNET/CRP source/runtime over-capacity behaviour, enemy-script bytecode basics.
- Multiple same-direction `$329` and `$346` guns are legal but use shared firing timers and may exhibit mismatched animation/projectile timing; **do not** impose a one-gun restriction.

When a task closes an open question, move its final answer into the corresponding permanent reference page, remove it from the active questions here and link to the new reference. Avoid duplicating the long technical detail across both pages.

## v0.3-specific research requests (12 October 2026)

- **Player ship source graphics and render position:** locate authentic player BOB/ship graphics, palette and drawing origin relative to the source `$02B` START tile. At present the optional HTML5 preview is explicitly schematic. Do not represent it as pixel-accurate original artwork until runtime code and graphics have been traced.
- **Post-level screen palette/staging:** the fixed 20×8 tile layouts at `$50A30` etc. are located and can be previewed. Confirm the original palette-selection and any dynamic overlays applied when these screens are displayed; v0.3 uses gameplay Palette B (with a manual Palette A comparison option).
- **More reusable visual tile groups:** the initial raw-map 2×2 patterns are evidence-backed but not exhaustive. Identify larger repeating groups (3×2, 4×2, border/edge motifs, animations) by map occurrence and visual inspection, distinguishing environmental patterns from semantic runtime entities. Do not allow their placement if a complete safe semantic mutation is not yet available.
