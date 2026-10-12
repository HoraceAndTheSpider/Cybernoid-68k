# Cybernoid Amiga reverse-engineering Wiki

The permanent human-readable reference for the Cybernoid Amiga GAME binary and the HTML5 level editor. The aim is to let future contributors understand the game, its memory structures and safe editing restrictions **without repeating already completed reverse engineering**.

Each game-reference page has (1) plain-language explanation of what the data represents and (2) technical offsets, runtime addresses, structures and behaviour. The original `data/GAME` and tested runtime are authoritative. Preserve raw values and original oddities rather than guessing repairs.

**Confidence:** **Verified** = backed by original binary/runtime code or tests; **Strong inference** = persuasive but partly unproved; **Unresolved** = deliberately kept as an open question. An application choice is not automatically an original-game discovery.

## Original game reference

1. [Project goal and method](01-project-goal-and-method.md)
2. [Binary layout and addresses](02-binary-layout-and-addresses.md)
3. [Levels, rooms and topology](03-levels-rooms-and-topology.md)
4. [Graphics, palettes and front-end screens](04-graphics-palettes-and-frontend.md)
5. [Special markers and semantic entities](05-special-markers-and-entities.md)
6. [Runtime object pools and capacity](06-runtime-object-pools.md)
7. [Automatic enemy scripts](07-automatic-enemy-scripts.md)
8. [Editor and repacking safety](08-editor-and-repacking-safety.md)
9. [Tile collision, solidity and destruction](10-tile-collision-and-destruction.md)

## Single investigation register

[**Further Investigations**](Further%20Investigations.md) — all unresolved research questions, next proofs and confidence gaps, including changeable room topology and variant GAME formats. This replaces the old `09-known-unknowns.md`; do not maintain two lists.

## Application reference

[**HTML5 Editor**](HTML5%20Editor.md) — current browser editor layout, tile drawing, binary decoding, saved edits, GAME export, limitations and test status. Keep application material separate from original game evidence.

## Authoritative project files

- `data/GAME` — original/reference game binary; export remains named `GAME` until WHDLoad integration is revisited.
- `app/index.html`, `app/cybernoid-data.js`, `app/cybernoid-app.js`, `app/style.css` — static browser editor.
- `tools/cybernoid_project.py` — lossless fixed-size source extraction/repack reference.
- `tools/cybernoid_semantics.py` — existing comprehensive structural audit reference.
- `tools/cybernoid_entities.py` and `tools/cybernoid_entity_ops.py` — established semantic entity models/operations still to port fully.
- `editor/cybernoid_editor.py` — original Pygame editor, retained as migration reference (not an HTML5 dependency).
- `docs/reverse-engineering-status.md` — compact historical status notes.

## Core safety principle

> A GAME → extracted/edited project → GAME round trip, with no edits, must be byte-for-byte identical. The HTML5 app independently applies ordinary map-cell changes to a copy of the original binary and exports an extensionless `GAME`; loader/BOOT integration is deferred.

Research should document the game; the app should enact supported operations using documented facts; both should be delivered together when a converted Python section reveals undocumented data.

## Documentation location and cleanup status

The current Markdown research pages are in `docs/wiki/`. The root `wiki/` directory currently holds reference images; these are **not yet** a complete mirrored set of the text pages. The owner plans to make the Wiki the permanent home of all knowledge in `docs/`, but **do not delete `docs/` yet**: `docs/semantic-entity-model.md`, `docs/reverse-engineering-status.md` and the DOCX handover still need a completeness comparison against the Wiki. The `outputs/` folder also contains research artefacts that should not be bulk-deleted until their evidence is reconciled.
