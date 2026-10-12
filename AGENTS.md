# Cybernoid 68k — project working instructions

## Purpose

This is a continuing reverse-engineering and HTML5 authoring project for **Cybernoid (Amiga)**. The primary goal is a safe, convenient browser-based editor that works on the original `GAME` data format. The current editor imports and exports the extensionless `GAME`. WHDLoad-specific file naming/loader integration is deferred until explicitly requested. Preserve all established knowledge about the original game binary.

## Sources and scope

1. **Read relevant project Wiki page(s) first** in `docs/wiki/`, then the owning implementation file(s). The Wiki is the durable, human-readable reference; do not repeat already settled reverse engineering without new contradictory evidence.
2. Cybernoid Dropbox folder `/Geek/Gaming Projects/Cybernoid 68k` is the preferred current file copy. GitHub is an additional reference; the owner synchronises and pushes changes.
3. Indy Heat's HTML5 editor at `HoraceAndTheSpider/Indy-Heat-WHD`, particularly reusable raster, brush and palette modules, is an architectural/design reference. Borrow resource-neutral functionality deliberately, not wholesale game-specific assumptions.
4. `data/GAME`, game runtime behaviour and owner testing are the final factual authorities. Treat any unclear layout/offset as unresolved and record it without guessing.
5. Do **not** modify Dropbox, GitHub or the owner's repository without a separate explicit request. Generate local replacement ZIPs by default.

## Deliverables (mandatory)

- **Always provide one downloadable ZIP** of changed/new complete production files, preserving repository-relative paths. Do not provide patches, code fragments, patch notes, or Python utilities as deliverables.
- Include only **new or replaced** files; do not rebundle original GAME, WHDLoad, binary assets, unchanged files or entire repositories without a request.
- If a file should be removed or renamed, **state the exact path to delete**. Do not silently delete files or require repository cleanup without advising the owner.
- For browser/editor work, include `app/index.html` in delivery packages even if only its dependencies changed, so the deployable HTML5 entry point is supplied with the changes.
- Verify JavaScript syntax and perform focused behavioural tests where possible. Clearly distinguish local synthetic/browser checks from testing on the owner's genuine GAME or Amiga/WHDLoad.
- The owner normally handles commits, pushes and Amiga tests; user-reported live results take precedence over static assumptions.

## Working modes

### Implementation tasks

Read only the relevant Wiki page(s) and owning code, make the requested change, perform a focused check, **deliver the ZIP**. Avoid broad unrelated research, repeated source retrieval, investigative loops or replacing working behaviour simply to reorganise code.

### Investigations

Research specific gaps, keep original source addresses/file offsets and evidence, and update a permanent game reference page whenever the finding is resolved. Maintain just **one** `docs/wiki/Further Investigations.md` for unsolved questions and proposed probes. Do not create separate speculative or chronological investigation pages.

## Wiki organisation

- `docs/wiki/README.md` is the navigation hub.
- Game-reference pages describe actual game behaviour and binary/runtime structures in plain English with technical addresses, formats, snippets and verification status.
- `docs/wiki/Further Investigations.md` is the single register of known unknowns, with questions, evidence and priorities. Move resolved facts into the appropriate permanent reference page.
- Keep editor-facing information in a **small number** of dedicated app reference pages (currently `docs/wiki/HTML5 Editor.md`). App implementation choices are not automatically game-engine facts.
- Every time Python code is converted to HTML5/JavaScript, check for undocumented original-game knowledge and update/create the corresponding Wiki reference **in the same delivery**. Cite Python source paths as evidence where direct disassembly references are unavailable.
- Preserve confidence distinctions: **Verified**, **Strong inference**, **Unresolved**. Never turn an assumption into a fact when converting code.

## Binary and edit safety

- Original GAME is **383,230 bytes** for the currently documented build. Export a complete **GAME** binary with unchanged original sections byte-for-byte preserved. Do not make assumptions about future modified WHDLoad BOOT or loader filename.
- Game runtime addresses in the extracted image correspond to file offset `runtime_address - $EE06`; check the Wiki for exceptions and for variant/release limits.
- Every gameplay room is 20×11 16-bit tile/control words, not a 20×12 screen. The 20×12 front-end faux room is separate.
- Levels 1–3 have distinct logical room IDs / physical room lookup entries; Level 4 uses a direct 8-wide room grid. Topology/navigation controls must not be hard-wired to a permanently fixed map. Changing active slots, transitions or tables remains **research-gated** until proven safe.
- Do not silently normalise out-of-range Level-4 words, original RNET/CRP overflows or ED-only endpoint layouts. Preserve the unusual verified original behaviour.
- Never modify a special marker or one cell of a multi-cell entity as an independent ordinary tile. Make export validation informative with level/room/cell whenever available.
- Fixed-size repacking is the default. Expanding tiles, scripts, room allocations or relocating code requires separate original-code investigation, not a speculative edit.
- Initial HTML5 milestone is a **safe subset** of the Python editor; do not describe its structural validation as full Python audit parity until genuinely ported and tested.

## UI baseline

- **Top toolbar:** Load GAME (extensionless file selection), Import Edits, Save Edits, Export GAME, Undo/Redo, Help.
- **Left:** Level/room navigation, topology information (potential future topology editing), overlays and view controls.
- **Centre:** Pixel-accurate zoomable room editing canvas.
- **Right:** Tile catalogue, drawing tools or contextual editor functions/inspector; eventual 16×16 pixel Tile Editor with reusable Indy Heat drawing primitives.
- Panels scroll independently; editor messages should be readable, specific and action-oriented. HTML5 application should run as static files, without Python or Node as a user dependency.
- Prefer complete browser-native binary import/export, with `index.html` always included in delivery ZIPs.

## Directory layout and housekeeping (October 2026)

- `app/` is the current HTML5 application. The earlier `editor/` now contains the **legacy Python** implementation; it is not the active app. Deliver replacement browser files under `app/`, never `editor/`.
- The owner's provided `app/Cybernoid Logo.png` is the branding asset. Keep it responsive, height/width constrained, and ensure it cannot dominate narrow layouts.
- `GAME` has **no extension**; the GAME file input MUST NOT set an `accept` extension or MIME filter. Validate after selection by contents and supported binary profile, then export `GAME` without an extension. Do not introduce alternate input/output filenames unless the owner requests WHDLoad logistics later.
- `docs/` contains historical evidence and a Markdown Wiki mirror (`docs/wiki/`). The intended canonical documentation is the project's **Wiki**; migrate/compare every page and unique datum before recommending removal. Do **not** claim it is safe to delete `docs/` until all documents (including DOCX handovers) have been assessed against the permanent Wiki.
- `outputs/` contains legacy generated research artefacts (CSVs, image atlases, ASM traces and potential duplicates). Treat these as potential evidence, not disposable build products. Identify redundant files only after checking whether their content is duplicated/preserved in Wiki or regenerable from current sources.
- `tools/` Python code and `editor/` legacy Python implementation remain reference/test baselines until JavaScript structural-audit and operation parity has been demonstrated. Deletion/archival requires an explicit recommendation and owner decision.
- Deliver **only complete new/replacement files in one ZIP**. Explain separately, outside the ZIP, any exact files the owner may delete; never silently delete.
