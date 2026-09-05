#!/usr/bin/env python3
"""Semantic decoding and structural validation for Cybernoid Amiga projects.

This module deliberately sits above the lossless raw model in
``tools/cybernoid_project.py``.  It never replaces raw room words or raw enemy-script
bytes.  The pygame editor and audit CLI can therefore use richer semantics without
making the repacker depend on inferred names.

Findings encoded here were verified against the current repository ``data/GAME`` on
4 September 2026.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

TILE_MAX = 0x3C0  # 961 tiles: IDs 0..960

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

KNOWN_ANOMALIES = {
    (4, 40, 2, 10): 0x086F,
    (4, 44, 5, 8): 0xB087,
    (4, 44, 6, 8): 0x8D26,
    (4, 47, 18, 9): 0x0F4B,
}

RNET_MARKERS = {0x1F0, 0x1F1, 0x1F4, 0x1F5}
CRP_MARKERS = {0x1FC, 0x1FD, 0x1FE, 0x1FF}
ELE_H_START, ELE_H_END = 0x1F6, 0x1F7
ELE_V_START, ELE_V_END = 0x1F8, 0x1F9

# The original maps prove that BOTTOM ST/ED markers may legally occupy either
# source row 9 or 10.  L4 R51 and R55 use row 9 intentionally; treating only
# literal row 10 as valid creates false-positive audit errors.  Other sides are
# consistently on their literal outer edge in this GAME.
EDGE_SIDES = {
    "BOTTOM": ({0x1E2, 0x1E3}, lambda x, y: y in (9, 10), 0x1E2, 0x1E3),
    "LEFT": ({0x1E4, 0x1E5}, lambda x, y: x == 0, 0x1E4, 0x1E5),
    "TOP": ({0x1E6, 0x1E7}, lambda x, y: y == 0, 0x1E6, 0x1E7),
    "RIGHT": ({0x1E8, 0x1E9}, lambda x, y: x == 19, 0x1E8, 0x1E9),
}

# Runtime live-object implications proved from the creation/allocation paths.
RNET_LIVE_CAPACITY = 8       # slots 34..41; allocator failure is checked
ELE_PAIR_CAPACITY = 5        # slots 43..52; two adjacent records per pair
CRP_DECLARED_CAPACITY = 6    # slots 70..75; original data exceeds this and caller
                             # does not guard allocator exhaustion
AUTO_ENEMY_CAPACITY = 15     # slots 54..68
ENEMY_PROJECTILE_CAPACITY = 9  # slots 119..127
GENERIC_CONTROLLER_CAPACITY = 56  # slots 157..212; the common allocator overflows to slot 213

# Source words that call the common generic-controller constructor at runtime $114C2.
# Each occurrence consumes one record from slots 157..212.  The ranges are phase/state
# tiles that are deliberately preserved as raw words in the project model.
GENERIC_CONTROLLER_VALUES = {
    0x09F, 0x1D5, 0x1E0, 0x1E1,
    0x200, 0x232, 0x242, 0x24D, 0x2E2, 0x2E6, 0x2EE,
    0x300, 0x30C, 0x31C, 0x329, 0x346,
}
GENERIC_CONTROLLER_RANGES = (
    (0x253, 0x256),
    (0x257, 0x25A),
    (0x25B, 0x25E),
    (0x25F, 0x262),
    (0x263, 0x266),
    (0x267, 0x26A),
    (0x26B, 0x26E),
)


def uses_generic_controller(value: int) -> bool:
    return value in GENERIC_CONTROLLER_VALUES or any(lo <= value <= hi for lo, hi in GENERIC_CONTROLLER_RANGES)


@dataclass(frozen=True)
class AuditIssue:
    severity: str
    code: str
    message: str
    level: int | None = None
    logical_room: int | None = None
    physical_room: int | None = None
    x: int | None = None
    y: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _signed8(value: int) -> int:
    return value - 0x100 if value & 0x80 else value


def decode_enemy_script(record: dict) -> list[dict]:
    """Decode one current automatic-enemy script while retaining raw byte ranges.

    Current interpreter semantics:
      $81       loop to post-header command start
      $82       create one enemy projectile
      $85       create three enemy projectiles
      $80 n dx dy
                repeat signed movement pair for n updates; if n=$84 the runtime
                uses random() & $3F as the count
      $83 n     stationary wait; if n=$84 runtime uses random() & $1F
      dx dy     otherwise, one signed movement pair

    The three-byte script header is object_count, animation_start, animation_end.
    object_count is 1 or 2 in the current library.  A value of 2 makes the spawn
    path seek/use an adjacent second live-object record.
    """
    raw = bytes.fromhex(record["raw_hex"])
    if len(raw) < 4:
        raise ValueError(f"script {record.get('name')} is too short")

    start = int(record["runtime_start"])
    i = 3
    commands: list[dict] = []
    while i < len(raw):
        command_offset = i
        runtime_addr = start + i
        op = raw[i]
        i += 1

        if op == 0x81:
            commands.append({
                "runtime_addr": runtime_addr,
                "offset": command_offset,
                "op": "LOOP",
                "raw_hex": "81",
            })
            if i != len(raw):
                raise ValueError(
                    f"script {record.get('name')} has bytes after $81 loop marker"
                )
            break

        if op == 0x82:
            commands.append({
                "runtime_addr": runtime_addr,
                "offset": command_offset,
                "op": "FIRE_ONE",
                "projectiles": 1,
                "raw_hex": "82",
            })
            continue

        if op == 0x85:
            commands.append({
                "runtime_addr": runtime_addr,
                "offset": command_offset,
                "op": "FIRE_THREE",
                "projectiles": 3,
                "raw_hex": "85",
            })
            continue

        if op == 0x80:
            if i + 2 >= len(raw):
                raise ValueError(f"script {record.get('name')} truncates $80 command")
            duration = raw[i]
            dx_raw, dy_raw = raw[i + 1], raw[i + 2]
            i += 3
            commands.append({
                "runtime_addr": runtime_addr,
                "offset": command_offset,
                "op": "MOVE_REPEAT",
                "duration_raw": duration,
                "duration": None if duration == 0x84 else duration,
                "duration_random_mask": 0x3F if duration == 0x84 else None,
                "dx": _signed8(dx_raw),
                "dy": _signed8(dy_raw),
                "raw_hex": bytes((op, duration, dx_raw, dy_raw)).hex(),
            })
            continue

        if op == 0x83:
            if i >= len(raw):
                raise ValueError(f"script {record.get('name')} truncates $83 command")
            duration = raw[i]
            i += 1
            commands.append({
                "runtime_addr": runtime_addr,
                "offset": command_offset,
                "op": "WAIT",
                "duration_raw": duration,
                "duration": None if duration == 0x84 else duration,
                "duration_random_mask": 0x1F if duration == 0x84 else None,
                "raw_hex": bytes((op, duration)).hex(),
            })
            continue

        if i >= len(raw):
            raise ValueError(f"script {record.get('name')} truncates movement pair")
        dy_raw = raw[i]
        i += 1
        commands.append({
            "runtime_addr": runtime_addr,
            "offset": command_offset,
            "op": "MOVE_ONCE",
            "dx": _signed8(op),
            "dy": _signed8(dy_raw),
            "raw_hex": bytes((op, dy_raw)).hex(),
        })

    if not commands or commands[-1]["op"] != "LOOP":
        raise ValueError(f"script {record.get('name')} has no final $81 loop marker")
    return commands


def iter_room_cells(room: dict) -> Iterator[tuple[int, int, int]]:
    rows = room["rows"]
    for y, row in enumerate(rows):
        for x, value in enumerate(row):
            yield x, y, int(value)


def marker_positions(room: dict, values: int | Iterable[int]) -> list[tuple[int, int, int]]:
    wanted = {values} if isinstance(values, int) else set(values)
    return [(x, y, value) for x, y, value in iter_room_cells(room) if value in wanted]


def refresh_room_derived(room: dict, level: int) -> None:
    """Refresh non-authoritative marker/anomaly overlays after raw tile edits."""
    markers = []
    anomalies = []
    physical = int(room["physical_id"])
    for x, y, value in iter_room_cells(room):
        if value in MARKERS:
            literal, kind = MARKERS[value]
            markers.append({
                "x": x, "y": y, "word": value,
                "literal": literal, "kind": kind,
            })
        key = (level, physical, x, y)
        if key in KNOWN_ANOMALIES:
            anomalies.append({
                "x": x,
                "y": y,
                "raw_word": value,
                "expected_raw_word": KNOWN_ANOMALIES[key],
                "candidate_low_byte_only": value & 0xFF,
                "status": (
                    "unresolved_preserve_raw"
                    if value == KNOWN_ANOMALIES[key]
                    else "edited_from_known_anomaly"
                ),
            })
    room["markers"] = markers
    room["anomalies"] = anomalies


def refresh_project_derived(model: dict) -> None:
    for level in model["levels"]:
        level_no = int(level["level"])
        for room in level["rooms"]:
            refresh_room_derived(room, level_no)


def _match_horizontal_ele(room: dict) -> tuple[list[tuple[tuple[int, int], tuple[int, int]]], list[tuple[int, int]], list[tuple[int, int]]]:
    starts = [(x, y) for x, y, _ in marker_positions(room, ELE_H_START)]
    ends = [(x, y) for x, y, _ in marker_positions(room, ELE_H_END)]
    pairs = []
    unmatched_starts = []
    remaining = set(ends)
    for sx, sy in sorted(starts, key=lambda p: (p[1], p[0])):
        candidates = sorted((ex, ey) for ex, ey in remaining if ey == sy and ex > sx)
        if not candidates:
            unmatched_starts.append((sx, sy))
            continue
        end = candidates[0]
        remaining.remove(end)
        pairs.append(((sx, sy), end))
    return pairs, unmatched_starts, sorted(remaining)


def _match_vertical_ele(room: dict) -> tuple[list[tuple[tuple[int, int], tuple[int, int]]], list[tuple[int, int]], list[tuple[int, int]]]:
    starts = [(x, y) for x, y, _ in marker_positions(room, ELE_V_START)]
    ends = [(x, y) for x, y, _ in marker_positions(room, ELE_V_END)]
    pairs = []
    unmatched_starts = []
    remaining = set(ends)
    for sx, sy in sorted(starts, key=lambda p: (p[0], p[1])):
        candidates = sorted((ex, ey) for ex, ey in remaining if ex == sx and ey > sy)
        if not candidates:
            unmatched_starts.append((sx, sy))
            continue
        end = candidates[0]
        remaining.remove(end)
        pairs.append(((sx, sy), end))
    return pairs, unmatched_starts, sorted(remaining)


def _cell(rows: list[list[int]], x: int, y: int) -> int | None:
    if not (0 <= x < 20 and 0 <= y < 11):
        return None
    return int(rows[y][x])


def _compound_failures(room: dict) -> list[tuple[str, int, int, str]]:
    rows = room["rows"]
    failures = []
    for x, y, value in iter_room_cells(room):
        if value == 0x300:
            req = [
                (0, 1, {0x066}),
                (-1, 2, {0x062}), (0, 2, {0x064}), (1, 2, {0x063}), (2, 2, {0x065}),
                (-1, 3, {0x05C}), (0, 3, {0x05D}), (1, 3, {0x05E}),
                (2, 3, {0x05F, 0x210}),
            ]
            kind = "$300 organic cannon"
        elif value == 0x30C:
            req = [
                (-1, -1, {0x116}), (0, -1, {0x117}), (1, -1, {0x118}), (2, -1, {0x119}),
                (-1, 0, {0x11A}), (1, 0, {0x30D}), (2, 0, {0x11D}),
                (-1, 1, {0x11E}), (0, 1, {0x30E}), (1, 1, {0x30F}),
            ]
            kind = "$30C cannon"
        elif value == 0x242:
            req = [(1, 0, {0x243}), (0, 1, {0x244}), (1, 1, {0x245})]
            kind = "$242 2x2 structure"
        elif value == 0x232:
            req = [
                (1, 0, {0x233}), (0, 1, {0x234}), (1, 1, {0x235}),
                (0, 2, {0x236}), (1, 2, {0x237}),
            ]
            kind = "$232 2x3 structure"
        elif value == 0x31C:
            req = [(1, 0, {0x31D})]
            kind = "$31C fixed cannon"
        elif value == 0x329:
            req = [(-3, 0, {0x326}), (-2, 0, {0x327}), (-1, 0, {0x328})]
            kind = "$329 right-facing gun"
        elif value == 0x346:
            req = [(1, 0, {0x347}), (2, 0, {0x348}), (3, 0, {0x349, 0x359})]
            kind = "$346 left-facing gun"
        else:
            continue
        for dx, dy, allowed in req:
            got = _cell(rows, x + dx, y + dy)
            if got not in allowed:
                allowed_text = "/".join(f"${v:03X}" for v in sorted(allowed))
                got_text = "outside room" if got is None else f"${got:04X}"
                failures.append((kind, x, y, f"offset ({dx:+d},{dy:+d}) expected {allowed_text}, got {got_text}"))
    return failures


def audit_project(model: dict) -> tuple[dict, list[AuditIssue]]:
    issues: list[AuditIssue] = []
    levels = {int(level["level"]): level for level in model["levels"]}
    fixed = model["fixed_blocks"]

    if set(levels) != {1, 2, 3, 4}:
        issues.append(AuditIssue("error", "level_set", "project must contain levels 1..4"))

    room_total = sum(len(level["rooms"]) for level in levels.values())
    if room_total != 150:
        issues.append(AuditIssue("error", "room_count", f"expected 150 physical rooms, found {room_total}"))

    rooms_by_level: dict[int, dict[int, dict]] = {}
    for level_no, level in levels.items():
        by_physical = {int(room["physical_id"]): room for room in level["rooms"]}
        rooms_by_level[level_no] = by_physical
        if len(by_physical) != len(level["rooms"]):
            issues.append(AuditIssue("error", "duplicate_physical_room", "duplicate physical room ID", level_no))
        for slot in level["logical_slots"]:
            physical = int(slot["physical_id"])
            if slot.get("active") and physical not in by_physical:
                issues.append(AuditIssue(
                    "error", "logical_physical_out_of_range",
                    f"active logical room {slot['logical_id']} maps to missing physical room {physical}",
                    level_no, int(slot["logical_id"]), physical,
                ))

    # START marker/table consistency.
    start_rooms = [int(v) for v in fixed["start_rooms"]]
    for level_no in range(1, 5):
        level = levels[level_no]
        all_starts = []
        for room in level["rooms"]:
            for x, y, _ in marker_positions(room, 0x02B):
                all_starts.append((int(room["physical_id"]), x, y))
        if len(all_starts) != 1:
            issues.append(AuditIssue(
                "error", "start_marker_count",
                f"expected exactly one START marker in level, found {len(all_starts)}", level_no,
            ))
            continue
        logical = start_rooms[level_no - 1]
        slots = {int(slot["logical_id"]): slot for slot in level["logical_slots"]}
        if logical not in slots:
            issues.append(AuditIssue("error", "start_room_missing", f"configured start logical room {logical} is not represented", level_no, logical))
            continue
        expected_physical = int(slots[logical]["physical_id"])
        actual_physical, x, y = all_starts[0]
        if actual_physical != expected_physical:
            issues.append(AuditIssue(
                "error", "start_marker_room_mismatch",
                f"START marker is in physical room {actual_physical}, but configured logical room {logical} maps to {expected_physical}",
                level_no, logical, actual_physical, x, y,
            ))

    # Landing pads: exactly one adjacent $324/$325 pair per level.
    for level_no, level in levels.items():
        pad_cells = []
        for room in level["rooms"]:
            p = int(room["physical_id"])
            for x, y, value in marker_positions(room, {0x324, 0x325}):
                pad_cells.append((p, x, y, value))
        valid = (
            len(pad_cells) == 2
            and {v for _, _, _, v in pad_cells} == {0x324, 0x325}
            and pad_cells[0][0] == pad_cells[1][0]
            and pad_cells[0][2] == pad_cells[1][2]
            and abs(pad_cells[0][1] - pad_cells[1][1]) == 1
            and next(c for c in pad_cells if c[3] == 0x324)[1] + 1
                == next(c for c in pad_cells if c[3] == 0x325)[1]
        )
        if not valid:
            issues.append(AuditIssue("error", "landing_pad_pair", f"level landing pad is not one adjacent $324/$325 pair: {pad_cells}", level_no))

    # Level-4 portals.  Runtime $16526 iterates all eight records and matches
    # current room plus trigger coordinates, so multiple portals in one source room
    # are valid if their trigger tiles differ.
    portal_records = fixed["portal_table"]["records"]
    l4 = rooms_by_level.get(4, {})
    marker_keys: dict[tuple[int, int, int], int] = {}
    for p, room in l4.items():
        for x, y, _ in marker_positions(room, 0x1D5):
            key = (p, x, y)
            marker_keys[key] = marker_keys.get(key, 0) + 1
    if sum(marker_keys.values()) != len(portal_records):
        issues.append(AuditIssue(
            "error", "portal_marker_count",
            f"portal table has {len(portal_records)} records but map has {sum(marker_keys.values())} $1D5 markers", 4
        ))

    record_keys: dict[tuple[int, int, int], int] = {}
    for record in portal_records:
        source = int(record["source_room"])
        if source not in l4:
            issues.append(AuditIssue("error", "portal_source_room", f"portal source room {source} is missing", 4, source, source))
            continue
        tx = int(record["trigger_x"]); ty = int(record["trigger_y"])
        if (tx - 32) % 16 or (ty - 24) % 16:
            issues.append(AuditIssue(
                "error", "portal_trigger_off_grid",
                f"portal record {record['index']} trigger ${tx:X},${ty:X} is not on the tile-centre grid",
                4, source, source,
            ))
            continue
        x = (tx - 32) // 16; y = (ty - 24) // 16
        if not (0 <= x < 20 and 0 <= y < 11):
            issues.append(AuditIssue(
                "error", "portal_trigger_out_of_room",
                f"portal record {record['index']} trigger resolves to tile ({x},{y}) outside 20x11",
                4, source, source, x, y,
            ))
            continue
        key = (source, x, y)
        record_keys[key] = record_keys.get(key, 0) + 1
        if marker_keys.get(key, 0) != 1:
            issues.append(AuditIssue(
                "error", "portal_trigger_marker_mismatch",
                f"portal record {record['index']} expects one $1D5 marker at room {source} tile ({x},{y}); found {marker_keys.get(key, 0)}",
                4, source, source, x, y,
            ))

        dest = int(record["destination_room"])
        dx = int(record["destination_x"]); dy = int(record["destination_y"])
        if dest not in l4:
            issues.append(AuditIssue("error", "portal_destination_room", f"portal destination room {dest} is missing", 4, source, source))
        elif (dx - 32) % 16 or (dy - 24) % 16:
            issues.append(AuditIssue(
                "error", "portal_destination_off_grid",
                f"portal record {record['index']} destination ${dx:X},${dy:X} is not on the tile-centre grid",
                4, source, source,
            ))
        else:
            dest_x = (dx - 32) // 16; dest_y = (dy - 24) // 16
            if not (0 <= dest_x < 20 and 0 <= dest_y < 11):
                issues.append(AuditIssue(
                    "error", "portal_destination_out_of_room",
                    f"portal record {record['index']} destination resolves to tile ({dest_x},{dest_y}) outside 20x11",
                    4, source, source, dest_x, dest_y,
                ))

    for key, count in record_keys.items():
        if count > 1:
            p, x, y = key
            issues.append(AuditIssue(
                "error", "portal_duplicate_trigger",
                f"{count} portal records share the same source trigger; runtime table order would make later records unreachable",
                4, p, p, x, y,
            ))
    for key, count in marker_keys.items():
        if key not in record_keys:
            p, x, y = key
            issues.append(AuditIssue(
                "error", "portal_orphan_marker",
                f"$1D5 marker has no portal record for room {p} tile ({x},{y})",
                4, p, p, x, y,
            ))

    # Per-room structure/entity checks.
    total_ele_pairs = 0
    edge_spawn_rooms = 0
    compound_counts = {"300": 0, "30C": 0, "242": 0, "232": 0, "31C": 0, "329": 0, "346": 0}
    max_rnet = (0, None)
    max_crp = (0, None)
    max_ele = (0, None)
    max_generic_controllers = (0, None)

    for level_no, level in levels.items():
        logical_refs: dict[int, list[int]] = {}
        for slot in level["logical_slots"]:
            if slot.get("active"):
                logical_refs.setdefault(int(slot["physical_id"]), []).append(int(slot["logical_id"]))
        for room in level["rooms"]:
            physical = int(room["physical_id"])
            logical = logical_refs.get(physical, [None])[0]

            generic_controller_count = sum(
                1 for _, _, value in iter_room_cells(room) if uses_generic_controller(value)
            )
            if generic_controller_count > max_generic_controllers[0]:
                max_generic_controllers = (generic_controller_count, (level_no, logical, physical))
            if generic_controller_count > GENERIC_CONTROLLER_CAPACITY:
                issues.append(AuditIssue(
                    "error", "generic_controller_pool_overflow",
                    f"room requests {generic_controller_count} generic controllers; runtime slots 157..212 only safely hold {GENERIC_CONTROLLER_CAPACITY}, and the next allocation reaches slot 213 beyond the cleared object array",
                    level_no, logical, physical,
                ))

            # Any source word outside the tile bank must be one of the four retained anomalies.
            for x, y, value in iter_room_cells(room):
                if value > TILE_MAX:
                    key = (level_no, physical, x, y)
                    if key in KNOWN_ANOMALIES and value == KNOWN_ANOMALIES[key]:
                        issues.append(AuditIssue(
                            "info", "known_raw_anomaly",
                            f"preserved unresolved raw word ${value:04X}", level_no, logical, physical, x, y,
                        ))
                    else:
                        issues.append(AuditIssue(
                            "error", "out_of_range_source_word",
                            f"source word ${value:04X} is outside tile/control range 0..${TILE_MAX:03X}",
                            level_no, logical, physical, x, y,
                        ))

            hpairs, hunmatched_start, hunmatched_end = _match_horizontal_ele(room)
            vpairs, vunmatched_start, vunmatched_end = _match_vertical_ele(room)
            pair_count = len(hpairs) + len(vpairs)
            total_ele_pairs += pair_count
            if pair_count > max_ele[0]:
                max_ele = (pair_count, (level_no, logical, physical))
            for x, y in hunmatched_start:
                issues.append(AuditIssue("error", "ele_horizontal_start_unmatched", "$1F6 has no $1F7 to its right on the same row", level_no, logical, physical, x, y))
            for x, y in hunmatched_end:
                issues.append(AuditIssue("error", "ele_horizontal_end_unmatched", "$1F7 has no unmatched $1F6 to its left on the same row", level_no, logical, physical, x, y))
            for x, y in vunmatched_start:
                issues.append(AuditIssue("error", "ele_vertical_start_unmatched", "$1F8 has no $1F9 below it in the same column", level_no, logical, physical, x, y))
            for x, y in vunmatched_end:
                issues.append(AuditIssue("error", "ele_vertical_end_unmatched", "$1F9 has no unmatched $1F8 above it in the same column", level_no, logical, physical, x, y))
            if pair_count > ELE_PAIR_CAPACITY:
                issues.append(AuditIssue(
                    "error", "ele_pool_overflow",
                    f"room has {pair_count} ELE pairs; runtime slots 43..52 only safely hold {ELE_PAIR_CAPACITY} pairs",
                    level_no, logical, physical,
                ))

            rnet_count = len(marker_positions(room, RNET_MARKERS))
            crp_count = len(marker_positions(room, CRP_MARKERS))
            if rnet_count > max_rnet[0]:
                max_rnet = (rnet_count, (level_no, logical, physical))
            if crp_count > max_crp[0]:
                max_crp = (crp_count, (level_no, logical, physical))
            if rnet_count > RNET_LIVE_CAPACITY:
                issues.append(AuditIssue(
                    "info", "rnet_runtime_cap",
                    f"room contains {rnet_count} RNET source markers; allocator only supplies {RNET_LIVE_CAPACITY} live primaries and later markers are skipped when full",
                    level_no, logical, physical,
                ))
            if crp_count > CRP_DECLARED_CAPACITY:
                issues.append(AuditIssue(
                    "info", "crp_original_over_capacity",
                    f"room contains {crp_count} CRP source markers although dedicated range is slots 70..75; the first excess marker is initialised into slot 76 and every later excess marker overwrites that same slot, so the room collapses to at most seven live crawler records and must not be auto-normalised",
                    level_no, logical, physical,
                ))

            right_gun_count = len(marker_positions(room, 0x329))
            left_gun_count = len(marker_positions(room, 0x346))
            if right_gun_count > 1:
                issues.append(AuditIssue(
                    "warning", "right_gun_shared_fire_timer",
                    f"room contains {right_gun_count} $329 guns; all share firing timer $3FF2C, so one mount can animate while another creates the projectile (original engine behaviour)",
                    level_no, logical, physical,
                ))
            if left_gun_count > 1:
                issues.append(AuditIssue(
                    "warning", "left_gun_shared_fire_timer",
                    f"room contains {left_gun_count} $346 guns; all share firing timer $3FF2A, so one mount can animate while another creates the projectile (original engine behaviour)",
                    level_no, logical, physical,
                ))

            # $24D is the sole controller anchor for a two-cell horizontal animation.
            # The source map must retain $24D immediately followed by $24E; the
            # later animation-frame IDs $24F-$252 are runtime-only in this GAME.
            for x, y, value in iter_room_cells(room):
                if value == 0x24D:
                    got = _cell(room["rows"], x + 1, y)
                    if got != 0x24E:
                        issues.append(AuditIssue(
                            "error", "animated_pair_24d_missing_24e",
                            f"$24D must be followed by $24E; got {'outside room' if got is None else f'${got:04X}'}",
                            level_no, logical, physical, x, y,
                        ))
                elif value == 0x24E:
                    got = _cell(room["rows"], x - 1, y)
                    if got != 0x24D:
                        issues.append(AuditIssue(
                            "error", "animated_pair_24e_orphan",
                            "$24E is not immediately preceded by its $24D controller anchor",
                            level_no, logical, physical, x, y,
                        ))

            # ST/ED markers write persistent global endpoints; they are not required to be a conventional pair.
            present_sides = []
            for side, (values, border_test, start_id, end_id) in EDGE_SIDES.items():
                positions = marker_positions(room, values)
                if not positions:
                    continue
                present_sides.append(side)
                for x, y, value in positions:
                    if not border_test(x, y):
                        issues.append(AuditIssue("error", "edge_spawn_marker_off_edge", f"{MARKERS[value][0]} marker is not on its corresponding room edge", level_no, logical, physical, x, y))
                count_start = sum(1 for _, _, value in positions if value == start_id)
                count_end = sum(1 for _, _, value in positions if value == end_id)
                if count_start != 1 or count_end != 1:
                    issues.append(AuditIssue(
                        "info", "edge_spawn_inherited_endpoint",
                        f"{side} edge-spawn markers are ST={count_start}, ED={count_end}; runtime endpoint words persist across room rebuilds, so this must not be normalised automatically",
                        level_no, logical, physical,
                    ))
            if present_sides:
                edge_spawn_rooms += 1
            if len(present_sides) > 1:
                issues.append(AuditIssue("error", "edge_spawn_multiple_sides", f"room uses automatic edge-spawn markers on multiple sides: {present_sides}", level_no, logical, physical))

            for kind, x, y, detail in _compound_failures(room):
                issues.append(AuditIssue("error", "compound_footprint", f"{kind}: {detail}", level_no, logical, physical, x, y))
            for _, _, value in iter_room_cells(room):
                if value == 0x300: compound_counts["300"] += 1
                elif value == 0x30C: compound_counts["30C"] += 1
                elif value == 0x242: compound_counts["242"] += 1
                elif value == 0x232: compound_counts["232"] += 1
                elif value == 0x31C: compound_counts["31C"] += 1
                elif value == 0x329: compound_counts["329"] += 1
                elif value == 0x346: compound_counts["346"] += 1

    # Enemy script decoding: all bytes in the current library should be understood.
    scripts = fixed["enemy_scripts"]
    decoded_script_count = 0
    for script in scripts:
        try:
            commands = decode_enemy_script(script)
            decoded_script_count += 1
            object_count = int(script["header"]["object_count"])
            if object_count not in (1, 2):
                issues.append(AuditIssue("warning", "script_object_count", f"script {script['name']} uses unverified object_count={object_count}"))
            if not commands:
                issues.append(AuditIssue("error", "empty_script", f"script {script['name']} decoded to no commands"))
        except ValueError as exc:
            issues.append(AuditIssue("error", "script_decode", str(exc)))

    summary = {
        "physical_rooms": room_total,
        "edge_spawn_rooms": edge_spawn_rooms,
        "ele_pairs": total_ele_pairs,
        "compound_anchors": compound_counts,
        "decoded_enemy_scripts": decoded_script_count,
        "max_rnet_markers": {"count": max_rnet[0], "room": max_rnet[1]},
        "max_crp_markers": {"count": max_crp[0], "room": max_crp[1]},
        "max_ele_pairs": {"count": max_ele[0], "room": max_ele[1]},
        "max_generic_controllers": {"count": max_generic_controllers[0], "room": max_generic_controllers[1]},
        "errors": sum(1 for issue in issues if issue.severity == "error"),
        "warnings": sum(1 for issue in issues if issue.severity == "warning"),
        "info": sum(1 for issue in issues if issue.severity == "info"),
    }
    return summary, issues


def write_enemy_script_csv(model: dict, path: Path) -> None:
    rows = []
    for script in model["fixed_blocks"]["enemy_scripts"]:
        header = script["header"]
        for index, command in enumerate(decode_enemy_script(script)):
            rows.append({
                "script": script["name"],
                "table_index": script["table_index"],
                "script_runtime_start": f"${int(script['runtime_start']):06X}",
                "script_runtime_end": f"${int(script['runtime_end_exclusive']) - 1:06X}",
                "object_count": header["object_count"],
                "animation_start": f"${int(header['animation_start']):02X}",
                "animation_end": f"${int(header['animation_end']):02X}",
                "command_index": index,
                "command_runtime": f"${int(command['runtime_addr']):06X}",
                "op": command["op"],
                "duration": command.get("duration", ""),
                "random_mask": (
                    f"${int(command['duration_random_mask']):02X}"
                    if command.get("duration_random_mask") is not None else ""
                ),
                "dx": command.get("dx", ""),
                "dy": command.get("dy", ""),
                "projectiles": command.get("projectiles", ""),
                "raw_hex": command["raw_hex"],
            })
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "script", "table_index", "script_runtime_start", "script_runtime_end",
        "object_count", "animation_start", "animation_end", "command_index",
        "command_runtime", "op", "duration", "random_mask", "dx", "dy",
        "projectiles", "raw_hex",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_project(project_dir: Path) -> dict:
    return json.loads((project_dir / "project.json").read_text(encoding="utf-8"))


def write_audit_json(summary: dict, issues: list[AuditIssue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"summary": summary, "issues": [issue.to_dict() for issue in issues]}, indent=2) + "\n",
        encoding="utf-8",
    )
