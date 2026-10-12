# Cybernoid Amiga — HTML5 Editor v0.7

Open `app/index.html` in a browser. Choose the original extensionless `GAME` file using **Load GAME**. Editing is entirely local: no server, Python or Node installation is needed. **Export GAME** downloads the full supported binary without overwriting your original file.

## Workspace

- **Top bar:** Load GAME, Import/Save Edits (JSON), Export GAME, Undo/Redo, Help.
- **Left:** four level maps, Menu / High scores, four End Level screens and HUD, zoom (200–600% in 50% steps), viewing overlays and schematic ship START preview. The additional screens and topology remain read-only.
- **Centre:** 20×11 gameplay-room canvas with Pencil, Line, Rectangle, Filled Rectangle and Fill.
- **Right:** searchable five-column tile catalogue and compact illustrated Tile Groups panel, cell inspector and editing/validation controls.

**Tile Groups:** choose a pattern or supported compound, then click the room to stamp the complete arrangement. To capture a group from retail room artwork, choose **Capture** and drag a rectangle over that room; **Export** saves a `.cygroup.json` file for later import or sharing. Unsupported source entities and groups from a different GAME profile remain reference-only.

## Current placement rules (v0.7)

The editor supports independent animated tiles `$253–$26E`, RACT `$1E0/$1E1`, particle emitter `$09F`, Level-4-only pit `$200/$2E2`, and complete `$24D`, `$232`, `$242`, `$300`, `$30C`, `$31C`, `$329` and `$346` mechanisms and their canonical owned cells. Choose an approved tile/anchor, enable room editing and click to place it.

**Ordinary scenery does not need clearing first.** A supported special object may overwrite existing unprotected room tiles—passable or solid—in one checked operation, with the original tiles saved for Undo. Existing special/control markers, compound-owned cells and known anomalous values remain protected from partial replacement. Entire stamps are rejected if out of bounds, structurally incomplete or beyond the 56-controller room limit. Save Edits / Import Edits use the same validation. Moving/deleting an existing mechanism requires a future dedicated semantic operation.

**Animations:** recognised frame sequences preview at a provisional 150 ms interval in gameplay rooms, individual/group tile previews and the four read-only end-level views. This is a visual approximation, not verified original-game timing; the binary itself is unaffected.

## Data and documentation

The browser validates the documented 383,230-byte `GAME` profile and preserves bytes outside accepted edited room cells. Export is source-preserving, but **full parity with the existing Python semantic audit has not yet been completed**. Original Amiga runtime testing remains the acceptance test.

The root `wiki/` folder is the canonical separately version-controlled project Wiki; see `wiki/HTML5 Editor.md` for detailed editor behaviour and `wiki/Further Investigations.md` for outstanding research. Retain `tools/`, historical `editor/`, `docs/` and `outputs/` until their code/evidence is fully reconciled.
