# Cybernoid Amiga editor / repacker status

This repository is now at the point where fixed-size room editing can be built on a
lossless extractor/repacker. The current priority is **not** broad relabelling of the
68000 binary: it is a byte-identical `GAME -> project -> GAME` path and validation of
safe editor operations.

## Confirmed binary layout used by the tooling

Runtime addresses are relocated addresses. For the main payload:

```text
runtime = file_offset + $EE06
file_offset = runtime - $EE06
```

`data/GAME` is 383,230 bytes. The last six file bytes (`$5D8F8-$5D8FD`) are zero and
sit beyond the `$007C + $5D87C` relocated payload calculation; they are therefore
retained verbatim by the project instead of being assigned invented semantics.

The zero word at runtime `$40848` is also retained separately. Level 1 map data begins
at `$4084A`. Its eleven source rows each contain one padding word after the 15 physical
20-tile room rows, giving 22 bytes of Level-1 row padding plus the separate `$40848`
word = the 24-byte difference between the map-region span and the 150-room tile payload.

### Gameplay maps

| Level | Active logical layout | Physical rooms | Lookup | Map base | Source-row stride |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 15 active slots in a 3x8 allocation | 15 | `$3FD66` (24 words) | `$4084A` | `$25A` |
| 2 | 23 active slots in a 4x8 allocation | 23 | `$3FD96` (32 words) | `$42228` | `$398` |
| 3 | 32 active slots, 4x8 | 32 | `$3FDD6` (32 words) | `$449B0` | `$500` |
| 4 | 80 direct slots, 10x8 | 80 | direct | `$480B0` | `$140` |

The inactive Level 1/2 lookup entries are real `$0000` words, **not** invalid/sentinel
values. A level editor must therefore prevent an accidentally opened border from
leading into an inactive logical slot, because the game would resolve that slot to
physical room 0.

Levels 1-3 physical room cell address:

```text
map_base + physical_room * $28 + y * source_row_stride + x * 2
```

Level 4 physical room cell address:

```text
$480B0 + (room >> 3) * $DC0 + (room & 7) * $28 + y * $140 + x * 2
```

### Other fixed-size editable blocks

| Data | Runtime address / range |
| --- | --- |
| Completion preview image | `$1DA90-$1F9CF` |
| Completion preview palette | `$1F9D0-$1F9EF` |
| Tile bank, IDs 0-960 | `$1FBE8-$3DC67` (961 x `$80`) |
| L1-3 level descriptor pairs | `$3FD4E-$3FD65` |
| Enemy script pointer table | `$3FCFC-$3FD3B` (16 longwords) |
| Start rooms | `$3FFB8-$3FFBF` |
| Source row strides | `$3FFC0-$3FFCF` (4 longwords) |
| Palette A | `$3FFD0-$3FFEF` |
| Palette B | `$3FFF0-$4000F` |
| Level-4 portal table | `$1659E-$165FD` (8 x 12-byte records) |
| Automatic-enemy script data | `$40217-$40401` inclusive |
| Post-level layouts | `$50A30-$50F2F` (4 x 20x8 words) |

The script pointer table order is BOTTOM variants 0-3, TOP 0-3, RIGHT 0-3, LEFT 0-3.
Every current script occupies the bytes from its start pointer to the next script start;
the final script ends with `$81` at `$40401`. The extractor keeps the exact raw bytes
and boundaries. Higher-level bytecode names should only be added as individual opcode
semantics are proven.

## Four unresolved Level-4 source words

These remain first-class raw values and must not be silently repaired:

| Room | x,y | Runtime | Raw | Low-byte-only candidate |
| --- | --- | ---: | ---: | ---: |
| 40 | 2,10 | `$4D1F4` | `$086F` | `$006F` |
| 44 | 5,8 | `$4D01A` | `$B087` | `$0087` |
| 44 | 6,8 | `$4D01C` | `$8D26` | `$0026` |
| 47 | 18,9 | `$4D1EC` | `$0F4B` | `$004B` |

All four fall inside the same aligned 512-byte file block `$3E200-$3E3FF`. Their low
bytes are plausible tile values, so isolated high-byte corruption is a useful working
hypothesis, but the candidates above are **not** authorised replacements. A second
trusted copy of the same release is still the best way to resolve them.

## Tool

`tools/cybernoid_project.py` provides the first conservative project path:

```bash
python tools/cybernoid_project.py verify data/GAME build/roundtrip
python tools/cybernoid_project.py extract data/GAME build/project
python tools/cybernoid_project.py repack build/project build/GAME.patched
```

The generated project keeps:

- an exact `source/GAME` base image;
- `project.json` with all 150 20x11 rooms, logical/physical mapping, fixed tables,
  portals, post-level layouts, palettes and raw automatic-enemy scripts;
- fixed-size tile and completion-preview blobs.

Repacking starts from the exact preserved source image and scatters the structured
fixed-size values back to their original addresses. Unknown bytes are never regenerated
or normalised. Script/tile/image growth is rejected rather than relocated silently.

## Next editor work

The graphical editor should sit on top of this project model, not write directly into
`GAME`. Before enabling each high-level operation, add validators for at least:

- inactive logical-room targets / row wrapping;
- portal `$1D5` marker and portal-table synchronisation;
- ELE start/end pairing;
- ST/ED pairing and side consistency;
- compound structure identity/destruction footprints;
- object-pool capacity for newly added markers;
- landing-pad and START-marker consistency.

A fuller recompilable 68000 source remains a later option only when edits need data
relocation, larger tables, more rooms, more portal records, more graphics or new code.
