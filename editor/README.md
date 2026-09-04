# Cybernoid pygame editor

This is the first graphical editor layer for the lossless Cybernoid Amiga project
format produced by `tools/cybernoid_project.py`.

It intentionally edits `project.json`, **not `data/GAME` directly**. The existing
fixed-size repacker remains the only path back to a game binary.

## Install

```bash
python -m pip install pygame
```

## Prepare a project

```bash
python tools/cybernoid_project.py verify data/GAME build/roundtrip
python tools/cybernoid_project.py extract data/GAME build/project
python tools/cybernoid_audit.py build/project \
  --json outputs/cybernoid_structural_audit.json \
  --scripts-csv outputs/cybernoid_enemy_scripts_decoded.csv
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

- `1`–`4`: select level
- click logical map: select room
- `P`: switch palette A/B for display (no unproved per-level palette assignment is assumed)
- `M`: semantic marker overlays
- `E`: enable/disable raw editing
- left-click tile palette: select tile/control ID
- left-click room while editing: paint selected raw word
- right-click room: eyedropper
- `Ctrl+Z`: undo
- `Ctrl+S`: save `project.json`
- `Ctrl+R`: validate and repack fixed-size `GAME.patched`
- `Esc`: quit

## Current safety policy

The GUI starts read-only. Raw painting is available because the extractor/repacker has
been verified byte-identically and every room source word remains authoritative.
However, raw editing can create invalid entity structures, so the semantic audit runs
after edits and repacking is blocked if it reports structural errors.

High-level **Add Entity** tools are deliberately not exposed yet. Current reverse
engineering shows different runtime capacity behaviour:

- RNET source markers instantiate into slots 34–41. The allocator failure is checked,
  so at most eight live primaries are created; original rooms can contain more markers.
- ELE pairs use two adjacent records from slots 43–52. More than five pairs would risk
  pool overflow and is rejected by the validator.
- CRP uses slots 70–75 but the marker loader does not guard allocator exhaustion; some
  original rooms already contain more than six CRP markers. Existing raw layouts must
  therefore be preserved rather than normalised.
- automatic edge-spawn enemies use slots 54–68; enemy projectiles use slots 119–127.

ST/ED markers are also intentionally **not** normalised into conventional pairs. The
runtime stores their coordinates in persistent globals; two original rooms use ED-only
configurations and inherit the previous start endpoint.
