# 8. Editor and repacking safety

This page documents **original game-data restrictions and safe editing principles**, separately from the two authoring implementations: the historical Python/Pygame editor and the new HTML5 editor. For the current browser's precise feature/validation coverage, see [HTML5 Editor](HTML5%20Editor.md).

## Two stages of authoring

**Original Python workflow:** `tools/cybernoid_project.py` extracts `data/GAME` to a `project.json` v2 model and fixed-size blobs. The Pygame interface edits `project.json`, then `repack_project()` validates fixed sizes and creates an output `GAME.patched`. Source size/hash checks ensure the Python project's source binary still matches its recorded reference. The comprehensive structural and entity audit lives in `tools/cybernoid_semantics.py` and related helper modules.

**HTML5 v0.2 workflow:** the browser selects the extensionless **`GAME`** source file through an unfiltered file picker, then validates the supported **383,230-byte** binary profile in JavaScript. It copies source bytes into memory, edits allowed ordinary 16-bit room words, and runs a bounded subset of structural checks before exporting a full-size **`GAME`** binary. Export does not overwrite local files. WHDLoad filename/loader handling is deferred. The browser editor does **not** depend on Python, but its audit is **not yet fully equivalent to the Python audit**.

**File handling distinction:** HTML5 **Save Edits** generates `cybernoid-edits.json` containing only edited room cells plus a source CRC32 and per-cell original values. **Export GAME** emits the complete binary. CRC32 is a mismatch guard for the portable edits file, not a cryptographic source signature. Nothing is silently pushed to Dropbox or GitHub.

## Central invariant

> An untouched GAME → extract/edit/repack → GAME must be byte-for-byte identical, without changing unknown bytes, unused padding, flags, anomaly words, scripts or graphics by accident.

The new HTML5 path keeps the original entire binary and writes only accepted tile-word changes at documented addresses. It does not patch source graphics or lookup tables in this milestone.

## Why validation can block export

The game does not have only independent graphic squares. Examples of data corruption to prevent:

- Missing or duplicate START marker versus the configured logical start room.
- Missing or separated `$324/$325` landing-pad pair.
- Level-4 `$1D5` trigger no longer matching one of eight 12-byte portal records.
- Unmatched ELE mover endpoints or more than five simultaneous pairs per room.
- A compound cannon or animation missing a required owned tile.
- More than 56 generic animation/controller records in one room.
- Accidentally changing the four unresolved Level-4 out-of-range raw words.
- Pointer/size/layout changes for structures that do **not** support relocation.

The HTML5 app reports the first core error with level and physical room/cell when available; the full detailed Python audit remains the current more comprehensive research reference until its checks have been ported.

## Original unusual data must remain unusual

Unusual original data **is not automatically an error**. The reader must preserve:

- ED-only automatic spawn arrangements, including Level-4 DOWN markers on source row 9 in rooms 51/55.
- RNET rooms with more source markers than the eight available live primaries: later markers are skipped.
- CRP rooms with excess source crawlers: six dedicated slots plus one shared overflow slot 76; later excess overwrite that slot.
- Four high-byte-looking Level-4 anomaly words (see [Further Investigations](Further%20Investigations.md)).
- Multiple same-direction `$329`/`$346` gun controllers with shared firing timer effects, rather than inventing a one-cannon-per-room rule.

An audit should describe these as original runtime conditions, not silently 'repair' them.

## Raw word edits versus semantic entities

**Raw painting** writes a selected tile/control word into a single 20×11 room square. It is appropriate only when its target and source cells are safe to treat independently. The initial browser editor restricts writes to **ordinary tile words**, and protects special controls and all cells in known anchored compound-object footprints.

**Semantic editing** means an operation updates related source-map cells and tables *atomically*, where proved safe. Examples from the verified Python operation model are:

- Move a portal trigger and update its matching record, not just the `$1D5` tile.
- Move both halves of a landing pad together.
- Move/delete all 11 owned cells of a `$30C` cannon while leaving its contextual bottom-right neighbour unchanged.
- Add an ELE pair only when its linked endpoints and five-pair room capacity are valid.
- Add a generic-controller-using entity only within the 56-record capacity.
- Preserve an explicit caller-supplied replacement tile/underlay when moving a marker, because each source square stores **one word** and no hidden underlay is kept.

The Python backend has implemented and tested semantic operations, but these are **not enabled in HTML5 v0.2**. Do not treat clickable single-cell raw painting as a replacement for atomic object editing.

## Fixed-size limits — verified current game model

Current conservative repacking rejects relocation/growth. It does not yet support adding a ninth Level-4 portal, expanding beyond 961 tile records, allocating new room-data blocks, extending enemy scripts beyond their existing allocations, or relocating major game code/data. Simply altering a room lookup is not proof that creating new map topology is safe; entry/exit logic and active slots require further investigation.

The game installer supports more than one edition. Different-size, different-descriptor or different-stride binaries are intentionally rejected by the current HTML5 loader; do not claim universal release support.

## Recommended safe testing procedure

1. Load a trusted original `GAME` and record edition and full file hash.
2. Perform a **no-edit** export; compare bytes with the original. It should match exactly.
3. Make one ordinary tile change in a spare room, then inspect the binary diff (expect exactly the intended two-byte word location; actual byte differences can be one or two).
4. Restore/import edits and confirm Undo/Redo and consistency of the level/room/cell inspector.
5. Run the structural audit; if it fails, do not apply the exported GAME to a game installation.
6. Test a disposable exported `GAME` against an appropriate game loader/runtime and confirm rendering, collision, entry/exit and progression. Keep loader-naming changes outside the editor until explicitly requested.
7. For any newly discovered engine restriction, update the appropriate permanent Wiki game-reference page and the [Further Investigations](Further%20Investigations.md) register as required.

The owner's live Amiga/FS-UAE result is the acceptance test. Local browser fixture checks alone are not proof that game execution works.
