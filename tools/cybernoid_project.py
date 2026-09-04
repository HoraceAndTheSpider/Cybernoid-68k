#!/usr/bin/env python3
"""Lossless Cybernoid (Amiga) GAME extractor/repacker foundation.

The tool deliberately separates raw binary representation from derived semantics.
A project retains an exact copy of the source GAME and structured editable data.
Repacking starts from that exact source image, applies only fixed-size known fields,
and therefore preserves all unknown/unmapped bytes verbatim.

Current scope is intentionally conservative: fixed-size room/map data, lookup tables,
start rooms, row strides, Level-4 portals, post-level layouts, palettes, tile bank,
and the 16 automatic-enemy script streams. No relocation or data growth is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

RUNTIME_DELTA = 0xEE06
EXPECTED_GAME_SIZE = 383_230
PROJECT_VERSION = 1

PREVIEW_ADDR = 0x1DA90
PREVIEW_SIZE = 0x1F40
PREVIEW_PALETTE_ADDR = 0x1F9D0
PALETTE_A_ADDR = 0x3FFD0
PALETTE_B_ADDR = 0x3FFF0
PALETTE_SIZE = 0x20

TILE_BANK_ADDR = 0x1FBE8
TILE_SIZE = 0x80
TILE_COUNT = 961
TILE_BANK_SIZE = TILE_SIZE * TILE_COUNT
TILE_BANK_END = TILE_BANK_ADDR + TILE_BANK_SIZE  # $3DC68

LEVEL_DESCRIPTOR_ADDR = 0x3FD4E
LEVEL_DESCRIPTOR_COUNT = 3
START_ROOMS_ADDR = 0x3FFB8
ROW_STRIDES_ADDR = 0x3FFC0
PREMAP_WORD_ADDR = 0x40848

PORTAL_TABLE_ADDR = 0x1659E
PORTAL_COUNT = 8
PORTAL_RECORD_SIZE = 12

POSTLEVEL_BASE = 0x50A30
POSTLEVEL_COUNT = 4
POSTLEVEL_WIDTH = 20
POSTLEVEL_HEIGHT = 8
POSTLEVEL_SIZE = POSTLEVEL_WIDTH * POSTLEVEL_HEIGHT * 2

SCRIPT_POINTER_TABLE_ADDR = 0x3FCFC
SCRIPT_COUNT = 16
SCRIPT_FINAL_END = 0x40402  # exclusive; final $81 terminator is at $40401
SCRIPT_NAMES = [
    "BOTTOM_0", "BOTTOM_1", "BOTTOM_2", "BOTTOM_3",
    "TOP_0", "TOP_1", "TOP_2", "TOP_3",
    "RIGHT_0", "RIGHT_1", "RIGHT_2", "RIGHT_3",
    "LEFT_0", "LEFT_1", "LEFT_2", "LEFT_3",
]

# Known raw anomalies. They are preserved exactly and are not normalised.
KNOWN_ANOMALIES = {
    (4, 40, 2, 10): 0x086F,
    (4, 44, 5, 8): 0xB087,
    (4, 44, 6, 8): 0x8D26,
    (4, 47, 18, 9): 0x0F4B,
}

# Semantic labels are overlays only; raw tile/control words remain authoritative.
MARKERS = {
    0x02B: ("START", "player_start"),
    0x09F: ("", "particle_emitter"),
    0x1D5: ("PORTAL", "level4_portal"),
    0x1E0: ("RACT DOWN", "reactor_animation"),
    0x1E1: ("RACT UP", "reactor_animation"),
    0x1E2: ("ST DOWN", "edge_spawn_start_bottom"),
    0x1E3: ("ED DOWN", "edge_spawn_end_bottom"),
    0x1E4: ("ST LEFT", "edge_spawn_start_left"),
    0x1E5: ("ED LEFT", "edge_spawn_end_left"),
    0x1E6: ("ST UP", "edge_spawn_start_top"),
    0x1E7: ("ED UP", "edge_spawn_end_top"),
    0x1E8: ("ST RIGHT", "edge_spawn_start_right"),
    0x1E9: ("ED RIGHT", "edge_spawn_end_right"),
    0x1F0: ("RNET", "rnet"),
    0x1F1: ("RNET", "rnet"),
    0x1F2: ("BNUS MCE", "cybermace_bonus"),
    0x1F3: ("BNUS WPN", "weapon_ammo_bonus"),
    0x1F4: ("RNET", "rnet"),
    0x1F5: ("RNET", "rnet"),
    0x1F6: ("ELE RIGHT", "paired_mover_horizontal_start"),
    0x1F7: ("ELE LEFT", "paired_mover_horizontal_end"),
    0x1F8: ("ELE DOWN", "paired_mover_vertical_start"),
    0x1F9: ("ELE UP", "paired_mover_vertical_end"),
    0x1FA: ("BACK FIRE", "back_fire_bonus"),
    0x1FC: ("CRP LFT SLO", "crawler"),
    0x1FD: ("CRP LFT FST", "crawler"),
    0x1FE: ("CRP RHT SLO", "crawler"),
    0x1FF: ("CRP RHT FST", "crawler"),
    0x200: ("", "level4_mixed_spawn_pit"),
    0x2E2: ("", "level4_mixed_spawn_pit"),
    0x300: ("", "organic_cannon"),
    0x30C: ("", "large_cannon"),
    0x31C: ("", "fixed_cannon"),
    0x324: ("", "landing_pad_left"),
    0x325: ("", "landing_pad_right"),
    0x329: ("", "right_gun"),
    0x346: ("", "left_gun"),
}


@dataclass(frozen=True)
class LevelLayout:
    level: int
    physical_count: int
    lookup_addr: int | None
    logical_slots: int
    active_logical_ids: tuple[int, ...]
    map_base: int
    source_row_stride: int


LEVELS = {
    1: LevelLayout(1, 15, 0x3FD66, 24,
                   tuple([0, 1, 2, 3, 4, 8, 9, 10, 11, 12, 16, 17, 18, 19, 20]),
                   0x4084A, 0x25A),
    2: LevelLayout(2, 23, 0x3FD96, 32,
                   tuple([0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13,
                          16, 17, 18, 19, 20, 21, 24, 25, 26, 27, 28]),
                   0x42228, 0x398),
    3: LevelLayout(3, 32, 0x3FDD6, 32, tuple(range(32)), 0x449B0, 0x500),
    4: LevelLayout(4, 80, None, 80, tuple(range(80)), 0x480B0, 0x140),
}


def runtime_to_offset(addr: int) -> int:
    off = addr - RUNTIME_DELTA
    if off < 0:
        raise ValueError(f"runtime address ${addr:X} precedes relocated payload")
    return off


def read_u16(data: bytes | bytearray, runtime_addr: int) -> int:
    return struct.unpack_from(">H", data, runtime_to_offset(runtime_addr))[0]


def read_u32(data: bytes | bytearray, runtime_addr: int) -> int:
    return struct.unpack_from(">I", data, runtime_to_offset(runtime_addr))[0]


def write_u16(data: bytearray, runtime_addr: int, value: int) -> None:
    struct.pack_into(">H", data, runtime_to_offset(runtime_addr), value & 0xFFFF)


def write_u32(data: bytearray, runtime_addr: int, value: int) -> None:
    struct.pack_into(">I", data, runtime_to_offset(runtime_addr), value & 0xFFFFFFFF)


def slice_runtime(data: bytes | bytearray, runtime_addr: int, size: int) -> bytes:
    off = runtime_to_offset(runtime_addr)
    return bytes(data[off:off + size])


def write_runtime(data: bytearray, runtime_addr: int, payload: bytes) -> None:
    off = runtime_to_offset(runtime_addr)
    data[off:off + len(payload)] = payload


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def room_cell_runtime(layout: LevelLayout, physical_id: int, x: int, y: int) -> int:
    if not (0 <= physical_id < layout.physical_count):
        raise ValueError(f"invalid physical room {physical_id} for level {layout.level}")
    if not (0 <= x < 20 and 0 <= y < 11):
        raise ValueError("room coordinates outside 20x11")
    if layout.level == 4:
        room_x = physical_id & 7
        room_y = physical_id >> 3
        first_row = layout.map_base + room_y * 0xDC0 + room_x * 0x28
    else:
        first_row = layout.map_base + physical_id * 0x28
    return first_row + y * layout.source_row_stride + x * 2


def extract_room(data: bytes, layout: LevelLayout, physical_id: int,
                 logical_refs: list[int]) -> dict:
    rows: list[list[int]] = []
    markers: list[dict] = []
    anomalies: list[dict] = []
    for y in range(11):
        row: list[int] = []
        for x in range(20):
            addr = room_cell_runtime(layout, physical_id, x, y)
            value = read_u16(data, addr)
            row.append(value)
            if value in MARKERS:
                literal, kind = MARKERS[value]
                markers.append({
                    "x": x, "y": y, "word": value,
                    "literal": literal, "kind": kind,
                })
            key = (layout.level, physical_id, x, y)
            if key in KNOWN_ANOMALIES:
                anomalies.append({
                    "x": x, "y": y, "runtime_addr": addr,
                    "raw_word": value,
                    "expected_raw_word": KNOWN_ANOMALIES[key],
                    "candidate_low_byte_only": value & 0x00FF,
                    "status": "unresolved_preserve_raw",
                })
        rows.append(row)
    return {
        "physical_id": physical_id,
        "logical_refs": logical_refs,
        "first_row_runtime_addr": room_cell_runtime(layout, physical_id, 0, 0),
        "rows": rows,
        "markers": markers,
        "anomalies": anomalies,
    }


def extract_scripts(data: bytes) -> tuple[list[int], list[dict]]:
    pointers = [read_u32(data, SCRIPT_POINTER_TABLE_ADDR + i * 4)
                for i in range(SCRIPT_COUNT)]
    sorted_starts = sorted(set(pointers))
    if len(sorted_starts) != SCRIPT_COUNT:
        raise ValueError("enemy script pointer table contains duplicate pointers")
    boundary: dict[int, int] = {}
    for i, start in enumerate(sorted_starts):
        boundary[start] = sorted_starts[i + 1] if i + 1 < len(sorted_starts) else SCRIPT_FINAL_END

    scripts: list[dict] = []
    for index, (name, start) in enumerate(zip(SCRIPT_NAMES, pointers)):
        end = boundary[start]
        raw = slice_runtime(data, start, end - start)
        if not raw or raw[-1] != 0x81:
            raise ValueError(
                f"script {name} ${start:X}-${end - 1:X} does not end in $81"
            )
        scripts.append({
            "table_index": index,
            "name": name,
            "runtime_start": start,
            "runtime_end_exclusive": end,
            "length": len(raw),
            "header": {
                "object_count": raw[0],
                "animation_start": raw[1],
                "animation_end": raw[2],
            },
            "raw_hex": raw.hex(),
        })
    return pointers, scripts


def extract_project(game_path: Path, project_dir: Path) -> None:
    game = game_path.read_bytes()
    if len(game) != EXPECTED_GAME_SIZE:
        raise ValueError(
            f"unexpected GAME size {len(game)} bytes; expected {EXPECTED_GAME_SIZE}"
        )

    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "source").mkdir(exist_ok=True)
    (project_dir / "blobs").mkdir(exist_ok=True)
    shutil.copyfile(game_path, project_dir / "source" / "GAME")

    # Exact fixed-size binary blobs retained separately from semantic JSON.
    (project_dir / "blobs" / "tile_bank.bin").write_bytes(
        slice_runtime(game, TILE_BANK_ADDR, TILE_BANK_SIZE)
    )
    (project_dir / "blobs" / "completion_preview.bin").write_bytes(
        slice_runtime(game, PREVIEW_ADDR, PREVIEW_SIZE)
    )

    level_descriptors = []
    for i in range(LEVEL_DESCRIPTOR_COUNT):
        a = LEVEL_DESCRIPTOR_ADDR + i * 8
        level_descriptors.append({
            "level": i + 1,
            "lookup_ptr": read_u32(game, a),
            "map_base": read_u32(game, a + 4),
        })

    start_rooms = [read_u16(game, START_ROOMS_ADDR + i * 2) for i in range(4)]
    row_strides = [read_u32(game, ROW_STRIDES_ADDR + i * 4) for i in range(4)]

    levels_json = []
    for level_no, layout in LEVELS.items():
        if layout.lookup_addr is not None:
            lookup_words = [read_u16(game, layout.lookup_addr + i * 2)
                            for i in range(layout.logical_slots)]
        else:
            lookup_words = list(range(layout.logical_slots))

        logical_slots = [
            {
                "logical_id": i,
                "grid_x": i & 7,
                "grid_y": i >> 3,
                "active": i in layout.active_logical_ids,
                "physical_id": lookup_words[i],
            }
            for i in range(layout.logical_slots)
        ]

        refs: dict[int, list[int]] = {i: [] for i in range(layout.physical_count)}
        for slot in logical_slots:
            if slot["active"] and 0 <= slot["physical_id"] < layout.physical_count:
                refs[slot["physical_id"]].append(slot["logical_id"])

        rooms = [extract_room(game, layout, p, refs[p])
                 for p in range(layout.physical_count)]
        levels_json.append({
            "level": level_no,
            "physical_count": layout.physical_count,
            "logical_slots": logical_slots,
            "lookup_runtime_addr": layout.lookup_addr,
            "map_base_runtime_addr": layout.map_base,
            "source_row_stride": layout.source_row_stride,
            "rooms": rooms,
        })

    level1_padding = [
        {
            "row": y,
            "runtime_addr": LEVELS[1].map_base + y * LEVELS[1].source_row_stride + 15 * 0x28,
            "word": read_u16(
                game,
                LEVELS[1].map_base + y * LEVELS[1].source_row_stride + 15 * 0x28,
            ),
        }
        for y in range(11)
    ]

    portals = []
    for i in range(PORTAL_COUNT):
        a = PORTAL_TABLE_ADDR + i * PORTAL_RECORD_SIZE
        vals = [read_u16(game, a + j * 2) for j in range(6)]
        portals.append({
            "index": i,
            "source_room": vals[0], "trigger_x": vals[1], "trigger_y": vals[2],
            "destination_room": vals[3], "destination_x": vals[4],
            "destination_y": vals[5],
        })

    postlevels = []
    for level_index in range(POSTLEVEL_COUNT):
        a = POSTLEVEL_BASE + level_index * POSTLEVEL_SIZE
        rows = []
        for y in range(POSTLEVEL_HEIGHT):
            rows.append([
                read_u16(game, a + (y * POSTLEVEL_WIDTH + x) * 2)
                for x in range(POSTLEVEL_WIDTH)
            ])
        postlevels.append({
            "level": level_index + 1,
            "runtime_addr": a,
            "rows": rows,
        })

    script_pointers, scripts = extract_scripts(game)

    model = {
        "project_version": PROJECT_VERSION,
        "source": {
            "filename": game_path.name,
            "size": len(game),
            "sha256": sha256(game),
            "runtime_delta": RUNTIME_DELTA,
            "relocated_source_file_offset": 0x7C,
            "six_byte_file_trailer_hex": game[-6:].hex(),
        },
        "fixed_blocks": {
            "completion_preview": {"runtime_addr": PREVIEW_ADDR, "size": PREVIEW_SIZE},
            "completion_preview_palette": {
                "runtime_addr": PREVIEW_PALETTE_ADDR,
                "words": [read_u16(game, PREVIEW_PALETTE_ADDR + i * 2) for i in range(16)],
            },
            "tile_bank": {
                "runtime_addr": TILE_BANK_ADDR,
                "runtime_end_exclusive": TILE_BANK_END,
                "tile_count": TILE_COUNT,
                "tile_size": TILE_SIZE,
            },
            "palette_a": {
                "runtime_addr": PALETTE_A_ADDR,
                "words": [read_u16(game, PALETTE_A_ADDR + i * 2) for i in range(16)],
            },
            "palette_b": {
                "runtime_addr": PALETTE_B_ADDR,
                "words": [read_u16(game, PALETTE_B_ADDR + i * 2) for i in range(16)],
            },
            "level_descriptors": level_descriptors,
            "start_rooms": start_rooms,
            "row_strides": row_strides,
            "premap_word": {
                "runtime_addr": PREMAP_WORD_ADDR,
                "word": read_u16(game, PREMAP_WORD_ADDR),
            },
            "level1_row_padding": level1_padding,
            "portal_table": {
                "runtime_addr": PORTAL_TABLE_ADDR,
                "records": portals,
            },
            "postlevel_layouts": postlevels,
            "enemy_script_pointer_table": {
                "runtime_addr": SCRIPT_POINTER_TABLE_ADDR,
                "pointers": script_pointers,
            },
            "enemy_scripts": scripts,
        },
        "levels": levels_json,
    }

    (project_dir / "project.json").write_text(
        json.dumps(model, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Extracted {game_path} -> {project_dir}")
    print(f"SHA-256: {model['source']['sha256']}")


def _require_shape(rows: Iterable[Iterable[int]], height: int, width: int, what: str) -> list[list[int]]:
    result = [list(r) for r in rows]
    if len(result) != height or any(len(r) != width for r in result):
        raise ValueError(f"{what} must be exactly {width}x{height}")
    return result


def repack_project(project_dir: Path, output_path: Path) -> None:
    model = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    if model.get("project_version") != PROJECT_VERSION:
        raise ValueError(f"unsupported project version {model.get('project_version')}")

    source_path = project_dir / "source" / "GAME"
    source = source_path.read_bytes()
    expected_hash = model["source"]["sha256"]
    if sha256(source) != expected_hash:
        raise ValueError("project source/GAME SHA-256 no longer matches project.json")
    game = bytearray(source)

    fixed = model["fixed_blocks"]

    # Graphics blobs are fixed-size; arbitrary growth is explicitly rejected.
    tile_bank = (project_dir / "blobs" / "tile_bank.bin").read_bytes()
    if len(tile_bank) != TILE_BANK_SIZE:
        raise ValueError(f"tile_bank.bin must be exactly {TILE_BANK_SIZE} bytes")
    write_runtime(game, TILE_BANK_ADDR, tile_bank)

    preview = (project_dir / "blobs" / "completion_preview.bin").read_bytes()
    if len(preview) != PREVIEW_SIZE:
        raise ValueError(f"completion_preview.bin must be exactly {PREVIEW_SIZE} bytes")
    write_runtime(game, PREVIEW_ADDR, preview)

    for key, addr in (("completion_preview_palette", PREVIEW_PALETTE_ADDR),
                      ("palette_a", PALETTE_A_ADDR),
                      ("palette_b", PALETTE_B_ADDR)):
        vals = fixed[key]["words"]
        if len(vals) != 16:
            raise ValueError(f"{key} requires 16 words")
        for i, value in enumerate(vals):
            write_u16(game, addr + i * 2, value)

    desc = fixed["level_descriptors"]
    if len(desc) != LEVEL_DESCRIPTOR_COUNT:
        raise ValueError("level_descriptors must contain three records")
    expected_desc = [(LEVELS[i + 1].lookup_addr, LEVELS[i + 1].map_base)
                     for i in range(LEVEL_DESCRIPTOR_COUNT)]
    for i, record in enumerate(desc):
        expected_lookup, expected_map = expected_desc[i]
        if record["lookup_ptr"] != expected_lookup or record["map_base"] != expected_map:
            raise ValueError(
                "level descriptor relocation is not supported by the fixed-size repacker"
            )


    starts = fixed["start_rooms"]
    if len(starts) != 4:
        raise ValueError("start_rooms must contain four words")
    for i, value in enumerate(starts):
        write_u16(game, START_ROOMS_ADDR + i * 2, value)

    strides = fixed["row_strides"]
    expected_strides = [LEVELS[i].source_row_stride for i in range(1, 5)]
    if strides != expected_strides:
        raise ValueError(
            "source row stride changes require relocation/reassembly and are not supported"
        )


    write_u16(game, PREMAP_WORD_ADDR, fixed["premap_word"]["word"])
    pads = fixed["level1_row_padding"]
    if len(pads) != 11:
        raise ValueError("level1_row_padding must contain 11 words")
    for record in pads:
        write_u16(game, record["runtime_addr"], record["word"])

    level_records = {record["level"]: record for record in model["levels"]}
    for level_no, layout in LEVELS.items():
        record = level_records[level_no]
        slots = record["logical_slots"]
        if len(slots) != layout.logical_slots:
            raise ValueError(f"level {level_no}: wrong logical slot count")
        if layout.lookup_addr is not None:
            for i, slot in enumerate(slots):
                # Preserve even inactive entries: in the original they are real zero words,
                # not synthetic sentinels.
                write_u16(game, layout.lookup_addr + i * 2, slot["physical_id"])

        rooms = record["rooms"]
        if len(rooms) != layout.physical_count:
            raise ValueError(f"level {level_no}: wrong physical room count")
        by_id = {room["physical_id"]: room for room in rooms}
        if set(by_id) != set(range(layout.physical_count)):
            raise ValueError(f"level {level_no}: physical room IDs are not complete/unique")
        for p in range(layout.physical_count):
            rows = _require_shape(by_id[p]["rows"], 11, 20, f"level {level_no} room {p}")
            for y, row in enumerate(rows):
                for x, value in enumerate(row):
                    write_u16(game, room_cell_runtime(layout, p, x, y), value)

    portal_records = fixed["portal_table"]["records"]
    if len(portal_records) != PORTAL_COUNT:
        raise ValueError("portal table must contain eight records")
    for i, record in enumerate(portal_records):
        vals = [record["source_room"], record["trigger_x"], record["trigger_y"],
                record["destination_room"], record["destination_x"], record["destination_y"]]
        a = PORTAL_TABLE_ADDR + i * PORTAL_RECORD_SIZE
        for j, value in enumerate(vals):
            write_u16(game, a + j * 2, value)

    postlevels = fixed["postlevel_layouts"]
    if len(postlevels) != POSTLEVEL_COUNT:
        raise ValueError("postlevel_layouts must contain four layouts")
    for i, record in enumerate(postlevels):
        rows = _require_shape(record["rows"], POSTLEVEL_HEIGHT, POSTLEVEL_WIDTH,
                              f"post-level layout {i + 1}")
        a = POSTLEVEL_BASE + i * POSTLEVEL_SIZE
        for y, row in enumerate(rows):
            for x, value in enumerate(row):
                write_u16(game, a + (y * POSTLEVEL_WIDTH + x) * 2, value)

    pointer_record = fixed["enemy_script_pointer_table"]
    pointers = pointer_record["pointers"]
    if len(pointers) != SCRIPT_COUNT:
        raise ValueError("enemy script pointer table must contain 16 pointers")
    for i, value in enumerate(pointers):
        write_u32(game, SCRIPT_POINTER_TABLE_ADDR + i * 4, value)

    scripts = fixed["enemy_scripts"]
    if len(scripts) != SCRIPT_COUNT:
        raise ValueError("enemy_scripts must contain 16 records")
    by_index = {record["table_index"]: record for record in scripts}
    for i in range(SCRIPT_COUNT):
        record = by_index[i]
        if pointers[i] != record["runtime_start"]:
            raise ValueError(
                f"script pointer {i} no longer matches its fixed script start; relocation is unsupported"
            )
        raw = bytes.fromhex(record["raw_hex"])
        start = record["runtime_start"]
        end = record["runtime_end_exclusive"]
        if len(raw) != end - start:
            raise ValueError(
                f"script {record['name']} length changed; relocation/growth is not supported"
            )
        if not raw or raw[-1] != 0x81:
            raise ValueError(f"script {record['name']} must retain final $81 terminator")
        write_runtime(game, start, raw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(game)
    print(f"Repacked -> {output_path}")
    print(f"SHA-256: {sha256(bytes(game))}")


def verify_roundtrip(game_path: Path, work_dir: Path) -> None:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    extract_project(game_path, work_dir)
    repacked = work_dir / "GAME.repacked"
    repack_project(work_dir, repacked)
    original = game_path.read_bytes()
    rebuilt = repacked.read_bytes()
    if original != rebuilt:
        for i, (a, b) in enumerate(zip(original, rebuilt)):
            if a != b:
                raise SystemExit(
                    f"ROUND-TRIP FAILED: first mismatch file offset ${i:06X}: "
                    f"original ${a:02X}, rebuilt ${b:02X}"
                )
        raise SystemExit("ROUND-TRIP FAILED: output length differs")
    print("ROUND-TRIP OK: rebuilt GAME is byte-for-byte identical")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    ex = sub.add_parser("extract", help="extract GAME into a lossless structured project")
    ex.add_argument("game", type=Path)
    ex.add_argument("project", type=Path)

    rp = sub.add_parser("repack", help="rebuild GAME from a project without relocation")
    rp.add_argument("project", type=Path)
    rp.add_argument("output", type=Path)

    vr = sub.add_parser("verify", help="extract then repack and require byte-identical output")
    vr.add_argument("game", type=Path)
    vr.add_argument("work", type=Path)

    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "extract":
        extract_project(args.game, args.project)
    elif args.command == "repack":
        repack_project(args.project, args.output)
    elif args.command == "verify":
        verify_roundtrip(args.game, args.work)


if __name__ == "__main__":
    main()
