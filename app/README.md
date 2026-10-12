# Cybernoid Amiga — HTML5 Editor v0.5

Open `app/index.html` in a current browser. No server, Python, Node or Internet connection is necessary to use the editor. The native extensionless `GAME` file is selected using **Load GAME**; do not rename it to `.bin` or `.game`. Source size/profile validation follows file selection. **Export GAME** saves a full-size `GAME` file; the browser does not overwrite the source on disk.

## Workspace

- **Top:** Load GAME, Import/Save Edits (JSON), Export GAME, Undo/Redo, Help, responsive Cybernoid logo (existing asset: `Cybernoid Logo.png`).
- **Left:** four level buttons, an eight-wide logical room map (physical mapping preserved), read-only Other Screens (shared Menu / High scores, End L1–L4, and gameplay HUD strip), zoom in 50% increments from 200% through 600%, grid/collision/control overlays, Palette A reference, and a **Show player at START** toggle. The player display is a schematic preview at the `$02B` source tile; it is not a recovered retail sprite and does not change GAME.
- **Centre:** room canvas, tiled painting tools and source-preserving import/export messages. Gameplay rooms: 20×11; menu/backdrop: 20×12; end-level views: 20×8; HUD: 20×2. Other Screens are read-only.
- **Right:** select **Individual tiles** (original 961 tiles, now five per row) or **Tile groups**. Recurring source-map 2×2 motifs can be stamped, all-or-nothing, using Pencil when room editing is enabled. Compound structure groups are shown for reference only. Every click/stamp is one Undo/Redo transaction; it cannot partially overwrite protected compound tiles.

## Tile groups

`tile-groups.js` contains a small curated starting catalogue. Recurring 2×2 patterns were counted directly in the GitHub `data/GAME` binary on 12 October 2026, using the established room map addressing. Counts are exact position matches (overlapping matches included) and do not imply runtime entity/brush handling by Cybernoid. Compound groups follow the existing semantic-entity research and **cannot** be placed until the entity mutation layer is converted and verified. Additional groups and wider brush shapes can be added later.

## Scope and safety

Only room-cell edits with permitted individual tile IDs or complete ordinary 2×2 groups are allowed. Protected control words, incomplete compound structures and known Level-4 anomalies remain unmodified. Special-screen previews, topology, 4-plane source graphics, palettes and the player marker do not write bytes. Unknown/disputed game data is preserved.

Validation remains narrower than the complete legacy Python audit. Continue retaining `editor/`, `tools/`, `docs/` and research `outputs/` until the equivalent documentation and functionality have been migrated and checked. Read `wiki/HTML5 Editor.md` and `wiki/Further Investigations.md` for editor design and unresolved research.

## v0.5 — capture and exchange tile groups

Open **Tile groups** on the right and press **Select group from room**. Drag across any rectangular area of a *gameplay room* and release. No edit permission is required and GAME is unchanged. The captured group shows its original 16-bit cell IDs; give it a name and choose **Export selected group** to download a `.cygroup.json` file. This small text file can be attached to a ChatGPT conversation for interpretation or integration into the regular groups catalogue. **Import group** reads the same format into the current session. A new GAME load clears session-only captures, so export anything you wish to retain.

The JSON stores `format`, `version`, `name`, `width`, `height`, row-major `tiles`, source provenance (source CRC32, level, logical/physical room and x/y) and `reference_only`. Import validates format, array size and 16-bit word bounds. Source-control words, out-of-bank values and known compound-owned components remain **reference-only**; they are allowed in shared files for research but are not stampable. Ordinary groups can still only be placed as an atomic, protected-cell-checked paint operation.

## v0.5 — animated previews

**Animate known tiles** is switched on by default in View. Room and tile-palette previews animate the verified cyclic source families `$24D/$24E`, `$253-$26E` and the RACT `$1E0/$1E1` controllers. The 220 ms phase interval is a temporary browser display rate, **not verified retail timing**. The underlying raw source word is unchanged, collision/hazard rules still operate on the source ID, and no animation is written to the GAME. Triggered cannon firing and other unproved animation sequences are not guessed. Turn the checkbox off to view unanimated source tile artwork.

The root `wiki/` directory contains the canonical GitHub Wiki checkout, while `docs/wiki/` holds historical copies. Keep the old documentation and Python tools until reconciliation/audit parity is complete.

If an imported group's source CRC32 does not match the loaded GAME, the group is still available for **reference and export** but is not permitted to stamp until the edition/source difference is investigated. This is an authoring guard, not a new original-game constraint.

## v0.5 — compact Tile Groups interface

- Tile Groups is a visual thumbnail grid. Click a preview to select it (visible border/tick); hover or focus for source details. A lock identifies reference-only objects.
- **Capture**, **Import**, **Export** sit on one compact row; the name field only appears for a selected personal group. Category selection: Patterns, Objects or My groups. A selected pattern stamps as a whole; reference objects cannot be placed.
- Longer instructions live in the Help dialog and canonical Wiki, not the tool panel. The redundant explanatory panels in View/Topology/Editing were also simplified.
- This pass does not unlock animated/special placement. Existing Python semantic operations provide candidate atomic editing contracts but must be ported/tested before the HTML5 user-facing controls are enabled.
