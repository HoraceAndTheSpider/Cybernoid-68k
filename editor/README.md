# Cybernoid pygame editor

This is the graphical editor layer for the lossless Cybernoid Amiga project format
produced by `tools/cybernoid_project.py`.

It edits `project.json`, **not `data/GAME` directly**. The fixed-size repacker remains
the only path back to a game binary.

## Install

```bash
python -m pip install pygame
```

## Prepare a project

The project format is now version 2 because the front-end faux room, HUD strip and
Level-4 palette override are represented explicitly. Re-extract `data/GAME` rather
than reusing an older build/project directory.

```bash
python tools/cybernoid_project.py verify data/GAME build/roundtrip
python tools/cybernoid_project.py extract data/GAME build/project
python tools/cybernoid_audit.py build/project \
  --json outputs/cybernoid_structural_audit.json \
  --scripts-csv outputs/cybernoid_enemy_scripts_decoded.csv
python tools/cybernoid_entity_audit.py build/project --out outputs/entity_audit
```

## Run the editor

```bash
python editor/cybernoid_editor.py build/project
```

Optional patched output path:

```bash
python editor/cybernoid_editor.py build/project --output build/GAME.patched
```

## Controls

Everything that has a keyboard shortcut also has an on-screen button in the left
`CONTROLS` panel. Keyboard use is optional.

- `1`–`4`: select level (also `L1`–`L4` buttons)
- click logical map: select room
- `P`: palette reference toggle
- `F`: actual shared 20x12 front-end/Hall-of-Fame faux-room preview
- `M`: marker overlay
- `V`: **Entity Overlay** (inspection only; not entity-edit mode yet)
- `G`: room grid on/off
- `X`: room display 1:1 / 2x
- `H`: built-in Help page
- `E`: enable/disable raw editing
- tile palette: mouse wheel or on-screen `UP` / `DOWN` buttons
- left-click tile palette: select tile/control ID
- left-click gameplay room while editing: paint selected raw word
- left-click gameplay room while read-only: inspect cell only
- right-click gameplay room: eyedropper + inspect cell
- `Ctrl+Z`: undo
- `Ctrl+S`: save `project.json`
- `Ctrl+R`: validate and export fixed-size `GAME.patched`
- `Esc`: quit (or close Help first)

The persistent `Last file action` text in the control panel confirms the path used by SAVE or EXPORT. If Export is blocked, it now shows the first blocking problem with its level, room and map-square location where available. The bottom status strip also changes colour for successful, warning or failed file actions.

### Room display

`1:1 / 2x` switches between:

- **1:1**: each Amiga source pixel is one desktop pixel; the 20x11 room is exactly
  320x176 pixels;
- **2x**: the same room doubled to 640x352 for easier inspection/editing.

The grid is independent. Turning the grid off while in 1:1 mode gives the cleanest
representation of the game room graphics.

### Entity Overlay

`Entity Overlay` is currently explanatory/display-only. It does not change what a
mouse click edits.

- cyan outline: cells proved to belong to one logical entity/compound;
- green `LIVE`: source marker receives its intended runtime slot;
- grey `SKIP`: source marker is present but its runtime pool is already full;
- orange `OVR`: CRP source survives in shared overflow slot 76.

The `ROOM DATA / INSPECTOR` panel shows the raw word, semantic marker, owning entity,
runtime role and edit policy for the cell under the pointer/last clicked cell.

### Special/control tiles and "what is underneath"

There is **not a second hidden background tile stored underneath a special marker** in
the source room. Each room cell stores one 16-bit word. A value such as START, PORTAL,
RNET, CRP, etc. is that actual source word; the room loader recognises it and may create
runtime objects/state from it. The numeric value can also correspond to a graphics tile.

For a future high-level Move/Delete operation, the replacement/underlay tile therefore
needs to be explicit. The editor must not guess which ordinary background tile should
appear after a marker is removed.

### Palette behaviour

- Levels 1–3 automatically use gameplay Palette B (`$3FFF0`).
- Level 4 uses Palette B with the eight-colour override from `$1CD10`.
- `P` shows Palette A as a reference on gameplay rooms.
- `F` shows the actual menu/Hall-of-Fame faux room using Palette A.

The front-end preview remains read-only for now and is also the intended preview scene
for the later palette editor.

## Semantic editing policy

The GUI still starts read-only. Raw painting remains available, but repacking is
blocked on structural errors. The new `tools/cybernoid_entities.py` module defines the
next high-level editor layer without yet depending on untested drag/drop UI.

Safe atomic families now include:

- `$24D/$24E` as one horizontal two-cell, five-frame animation;
- `$253-$26E` as independent one-cell animation families;
- RACT `$1E0/$1E1` as independent one-cell animation controllers;
- `$232` 2x3, `$242` 2x2, `$300` 10-cell and `$30C` 11-owned-cell compound structures;
- single-cell `$31C/$329/$346` firing controllers;
- Level-4 `$200/$2E2` mixed spawn pits;
- `$09F` particle emitters, with a shared transient child-pool warning;
- ELE endpoint pairs, up to five pairs per room.

Fixed-count structures are **move/re-target rather than Add/Delete**:

- eight Level-4 portals (`$1D5` + eight 12-byte records);
- one START marker/table entry per level;
- one adjacent `$324/$325` landing pad per level.

RNET and CRP are presented using their actual row-major room-load roles. RNET creates
only the first eight primaries; later source markers are skipped. CRP creates six
dedicated records and one slot-76 overflow record; every excess marker after the sixth
overwrites that same slot, so only the final excess source survives in slot 76.

ST/ED remains an advanced/raw-preserving family because its endpoint globals persist
between room builds and the original game contains non-conventional ED-only layouts.

## Semantic operation backend

`tools/cybernoid_entity_ops.py` contains the tested high-level mutations that the GUI
will call next. They cover synchronised portal/START/landing movement, ELE pairs,
compound objects, `$24D/$24E`, approved one-cell controllers and conservative RNET/CRP
operations. The UI has not yet exposed those destructive operations.

Run the non-GUI tests from the repository root:

```bash
python -m unittest tools/test_cybernoid_entities.py -v
python -m unittest tools/test_cybernoid_entity_ops.py -v
```

## Deeper documentation

The built-in Help page is intentionally aimed at using the editor rather than explaining
68000 memory layouts or reverse-engineering terminology.

The fuller research reference is in [`docs/wiki/README.md`](../docs/wiki/README.md).
It explains the room structure, palettes, front-end faux room, special markers, runtime
object pools, automatic enemy scripts, safety rules and the remaining unresolved areas.

## Tile behaviour colours

The tile palette is colour-coded from the game's real collision/destruction rules:

- green: passable;
- red: solid;
- orange: destructible;
- purple: special/control value;
- yellow: Level-4 energy hazard.

Use **Collision [C]** to draw the same classification over the current room. The Room Data / Inspector also reports the selected/hovered tile's movement and destruction behaviour.

The side-gun "tips" are compound source objects, not safe one-cell placements:

- `$31C` requires `$31D`;
- `$329` requires `$326/$327/$328` to its left;
- `$346` requires `$347/$348/$349` to its right (one original `$359` end-cap variant).

Multiple `$329`/`$346` guns are legal original data, but same-direction guns share a firing timer and can show the projectile on one mount while another mount animates.
