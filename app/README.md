# Cybernoid — HTML5 Editor (v0.2)

Open `app/index.html` directly in a modern browser. **No installation, Python, Node or server is required.** All processing is local; the chosen file is not uploaded.

## Open and export GAME

1. Select **Load GAME**, choose your Cybernoid Amiga `GAME` file (with **no file extension**). The file picker deliberately has **no file type filter** so native Amiga filenames can be selected on macOS/Windows and mobile browsers.
2. The editor checks the binary size (383,230 bytes), known map descriptors and row strides **after** reading it. Other files may appear in the picker but will be rejected with a clear error; no source file is modified by loading it.
3. Navigate levels and rooms on the left, inspect tiles on the right. To paint ordinary tiles, enable room tile painting. Control markers and components of compound entities remain protected.
4. Use **Check current GAME** and **Export GAME**. Export downloads a complete binary named `GAME` with source bytes retained outside edited room cells. The browser never overwrites the selected local source file.
5. **Save Edits** and **Import Edits** exchange a source-bound JSON file containing changed room cells. JSON edits are not a GAME binary and cannot be directly loaded with Load GAME.

## Layout

- **Top:** bounded logo; Load GAME, Import Edits, Save Edits, Export GAME, Undo/Redo and Help.
- **Left:** four levels, logical room grid with physical-room mapping, grid/overlays and zoom. Topology editing is an explicit future research topic, not a current option.
- **Centre:** source 20×11 tile room (320×176 native pixels), displayed at integer zoom and with room drawing tools.
- **Right:** 961-tile palette, tile classification filters, cell inspector, safe painting option and audit summary.

The supplied `Cybernoid Logo.png` is a normal, local `app/` asset. CSS constrains its width/height and adapts to smaller screens; the full original PNG is deliberately not stretched to its source dimensions.

## First-release scope and caution

The HTML5 project uses binary format information recovered by the older Python code, but the browser does not run Python. The original `editor/` implementation and `tools/` are retained for reference and comparison. HTML5 audit parity with those legacy tools has **not** yet been established. There is no pixel-level tile editor or topology writer yet.

The currently documented binary profile is a fixed-size release. Do not assume a different release will load safely just because its filename is `GAME`. A clean round-trip must preserve all bytes; the owner’s original-game tests remain decisive.

The Wiki contains the original-game research and HTML5 editor reference. Documentation migration from `docs/` to the root `wiki/` is a **separate, not-yet-complete housekeeping task**. Do not delete `docs/`, `outputs/` or `editor/` solely because this HTML5 app runs.
