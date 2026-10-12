# Cybernoid HTML5 Editor — architecture and authoring contract

**Current milestone:** v0.2 (12 October 2026). This is an application reference, **not** new evidence about how the original game works. Original binary findings remain on the numbered game-reference pages. The browser app lives in `app/`; launch `app/index.html`. The Python editor remains read-only legacy reference and is not a runtime dependency.

## Native Amiga filename support (v0.2)

The Amiga file is named **`GAME` without a dot-extension**. The former file-picker `accept` attribute filtered by `.game`, `.bin` and a MIME type, which hid the real file in some macOS/browser selection dialogs. The `app/index.html` input now intentionally has **no `accept` filter**: the browser shows all file names and uses the `Game` constructor to validate supported size, descriptors and source row strides *after* selection. Accepting a filename in the picker is not the same as accepting its binary contents.

The top bar consistently says **Load GAME / Export GAME**. Downloads retain the extensionless `GAME` name. The Cybernoid logo is loaded from `app/Cybernoid Logo.png`; responsive CSS constrains its display width and height even on phones. The app is a static site with relative paths within `app/`, not the legacy Python `editor/` directory.

## Layout

- **Top toolbar:** Load GAME; Import Edits JSON; Save Edits JSON; Export GAME; Undo/Redo; Help.
- **Left:** level buttons, graphical logical room grid, physical-room mapping details, zoom and overlays. Future topology editing is intentionally accommodated in the design but disabled.
- **Centre:** native 320×176 gameplay room displayed at integer zoom; drawing modes and messages.
- **Right:** original 961-tile palette, tile-ID search, classification filter, current tile/cell inspector, edit enabling and audit status.

Panels scroll independently. 20×11 room coordinates map to x/y tile cells. The separate 20×12 front-end screen is deliberately **not** presented as a gameplay room.

## Source model and navigation

The core file `app/cybernoid-data.js` reads the complete supported **383,230-byte** GAME binary into memory. It retains an untouched original byte array and a mutable copy. It checks three level descriptors and all four row-stride values before allowing editing. This is a safety gate against unsupported release/layout variants, **not** proof that all supported-size releases are equivalent.

`Game.layout(level)` contains the allocated logical grid and active slots; `Game.physical(level, logical)` resolves the actual room to display. Runtime addresses convert to file offsets with `offset = runtime - $EE06`, as documented by `tools/cybernoid_project.py`. `Game.roomAddress(level,p,x,y)` handles row-interleaving and Level-4 eight-wide packing. The left-hand map's grid is **presentation**. Changing map topology is research-gated; no adjacency tables, lookup entries or source room packing are rewritten in this release.

See [Levels, rooms and topology](03-levels-rooms-and-topology.md) for the actual address formulae and [Further Investigations](Further%20Investigations.md) for topology research questions.

## Rendering

The browser decodes the original `$1FBE8` bank of 961 16×16, 4-plane tiles into a disposable off-screen Canvas atlas. For each scanline, four big-endian words are consumed in **plane order 0, 1, 2, 3**; bit 15 is leftmost, bit 0 rightmost; the bits combine into a four-bit palette index (`plane 0` = bit 0). Each palette entry is a 12-bit Amiga `$RGB` word with each nibble expanded from `0..15` to `0..255` by multiplying by 17.

Gameplay uses Palette B (`$3FFF0`) in Levels 1–3. Level 4 uses Palette B with indices 0–7 overridden from `$1CD10`. The optional Palette A (`$3FFD0`) toggle is **display-only**. The artwork atlas is regenerated on level/palette-mode changes; no palette values are written by the first release. See [Graphics, palettes and front-end](04-graphics-palettes-and-frontend.md).

## Supported editing operations

Pencil, line (Bresenham geometry), rectangle outline, filled rectangle and bounded same-tile flood-fill operate on **tile IDs**, not pixels. Right-click samples a tile. Undo/Redo group each mouse gesture as one transaction. Geometry here follows the reusable resource-neutral *style* of Indy Heat's `layer-tools.js`; there is no imported Indy Heat game-specific code or brush binary format in v0.2.

**Safety contract:** The editor will not place a value marked as a special/animated control or replace a protected source value/known compound-object footprint. This guards against accidentally removing just the tip of a gun or one cell of another atomic object. Ordinary source tile words can be painted. More advanced semantic operations will be added only after a complete version of the existing entity-operation checks has been transferred.

Current protections cover control markers and anchored footprints including `$232`, `$242`, `$24D`, `$300`, `$30C`, `$31C`, `$329`, `$346`, and the landing-pad pair. Four unexplained Level-4 out-of-range words are retained and protected.

## Saving, import and GAME export

**Save Edits** writes a text JSON patch with format name `cybernoid-html5-edits`, version 1, source file CRC32/length and per-cell `{level,p,x,y,before,after}` records. **Import Edits** validates the base source CRC32, cell bounds, unique coordinates, expected before-values and safe placement rules before applying changes. The CRC32 is a convenience guard against accidental mismatches, **not** an authenticity signature.

**Export GAME** generates a *whole* binary by copying the loaded source bytes and writing current edited map words at their documented two-byte offsets. It produces exactly 383,230 bytes for the supported game. Unedited bytes, including source quirks and unmapped blocks, are unchanged. An untouched import→export is byte-identical by construction.

The HTML5 app outputs **GAME** as a full binary and does not overwrite the loaded file on disk. WHDLoad-specific filename and loader changes are deferred until the owner requests that integration; the editor does not alter the WHDLoad slave or BOOT.

## Validation scope — important

v0.2 runs a **bounded, new browser-native audit**: logical mapping sanity; one START source per level matching the start-room table; adjacent `$324/$325` pads; eight Level-4 portal records with trigger/destination grid checks; verified compound footprints; ELE paired endpoints; ≤56 generic controllers per room; and out-of-range room words except the four known anomalies. Errors block GAME export and the status includes the first affected level/physical room/cell where known.

**Not yet equivalent to** `tools/cybernoid_semantics.py` or the full existing Python entity audit. In particular v0.2 does not perform all cross-room warnings, ST/ED inheritance checks or automatic enemy script validation. An audit PASS must not be represented as a complete semantic guarantee or as an Amiga runtime test. Retain the Python tools as reference until parity is verified.

## Known limitations / next milestones

1. Validate exact graphics and source-preserving binary export with the owner's actual GAME; native execution testing is separate.
2. Port remaining semantic validation and atomic entity operations before enabling special-object editing.
3. Provide a separate Tile Editor mode: enlarge an authentic 16×16 indexed raster, adapt reusable Indy Heat pixel tools/stencils/brushes, and write back `$80`-byte planar tile records using the proven format.
4. Investigate runtime room-entry/exit checks and logical slot activation before enabling topology editing on the left.
5. Add controlled palette edit screens and support for original release-profile differences.

## Verification for v0.2

- JavaScript syntax checks passed for `app/cybernoid-app.js` and `app/cybernoid-data.js`.
- A Node-based test loaded the **synthetic 383,230-byte fixture** through the browser binary-model code, verified four level layouts, core audit PASS, and a byte-identical no-edit binary output.
- Static HTML inspection confirmed the `GAME` input has **no `accept` filter**, the toolbar uses `GAME`, and the logo has a relative file URL with bounded responsive CSS sizing.
- A new headless-Chromium UI test was attempted but browser navigation was blocked by the test environment; **v0.2 UI and local filename-selector behaviour still require owner browser testing**. Prior v0.1 browser tests do not constitute v0.2 runtime confirmation.

This is **not** a verified test against the owner's original GAME, actual operating-system file chooser, or native Amiga/WHDLoad execution.

## v0.3: Navigation, palette and tile groups (12 October 2026)

The **Individual tiles** selection is now five columns wide (5 × 54 CSS canvas pixels = 270 px), avoiding the horizontal overflow caused by the former six-column 324 px palette. Indexed tile images still use nearest-neighbour display. Canvas hit-testing uses the same five-column indexing. Zoom now permits 200, 250, 300, 350, 400, 450, 500, 550 and 600 per cent, including +/- keyboard steps. The selected zoom applies to every screen's native canvas dimensions, rather than assuming 20×11 height.

The left-hand **Other Screens** row restores screens from the original GAME without allowing unsupported writes:

| Selection | Original binary source (runtime address) | Tile layout | Display palette |
| --- | --- | --- | --- |
| Menu / High scores | `$50F30` | 20×12 shared faux room | A `$3FFD0` |
| End Level 1 | `$50A30` | 20×8 | Gameplay B by default (presentation palette not yet independently traced) |
| End Level 2 | `$50B70` | 20×8 | Gameplay B by default |
| End Level 3 | `$50CB0` | 20×8 | Gameplay B by default |
| End Level 4 | `$50DF0` | 20×8 | Gameplay B with Level-4 override by default (actual staging untraced) |
| Gameplay HUD strip | `$3FF4E` | 20×2 | Current gameplay palette |

Post-level offsets are sequential `base + (level-1) × $140` (320 bytes per screen). The front-end reuses one tile-template behind menu/high-score text, which is drawn separately by the original game; the editor therefore does not claim to show the complete dynamic menu/high-score presentation. The existing Palette A reference switch still allows comparing palettes for post-level/HUD views; front-end always uses A. Previewing End Level 4 selects the documented eight-colour Level-4 override even if the last gameplay room visited belonged to another level. Runtime palette staging for the presentation screen itself remains under investigation. All these viewers are read-only by design.

The optional **Show player at START** draws a schematic ship outline at a `$02B` tile if the current gameplay room contains one. It does not load graphics or write bytes and must not be confused with authentic player BOB/sprite artwork. Recovering the authentic player artwork and positioning is on [Further Investigations](Further%20Investigations.md).

### Alternative grouped tile selector

`app/tile-groups.js` contains two categories. **Recurring artwork** consists of 2×2 patterns actually counted in the original GAME maps, which can be placed as whole stamps using Pencil. An attempted stamp that overlaps any protected tile or extends outside a room is refused in its entirety. `Game.commit()` receives the collection as one transaction for Undo/Redo. **Compound objects** are reference-only because placing `$242`, `$232`, `$31C`, `$329` and `$346` without their full semantic rules would create unsafe runtime objects. The group selector does not claim these recurring patterns are original engine-managed entities.

The extracted pattern counts and examples (from original `data/GAME`, GitHub `master`, 12 October 2026) are recorded in [Graphics and palettes](04-graphics-palettes-and-frontend.md). New source findings discovered while converting Python should be recorded in their game-reference pages, not only here.

**Testing boundary:** these are browser-editor implementation behaviours. There is not yet a verified end-to-end live Amiga test for v0.3; the original game's animation, player sprite and non-gameplay palette behaviour remain separate topics.
