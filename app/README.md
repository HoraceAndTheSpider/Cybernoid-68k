# Cybernoid Amiga — HTML5 Editor v0.3

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

Validation remains narrower than the complete legacy Python audit. Continue retaining `editor/`, `tools/`, `docs/` and research `outputs/` until the equivalent documentation and functionality have been migrated and checked. Read `docs/wiki/HTML5 Editor.md` and `docs/wiki/Further Investigations.md` for editor design and unresolved research.
