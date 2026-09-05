#!/usr/bin/env python3
"""Higher-level entity model for Cybernoid Amiga room editing.

This module deliberately sits above the raw 20x11 word maps.  It groups only
structures whose runtime relationship has been demonstrated from the GAME binary,
and exposes runtime-capacity roles that a pygame editor can present before making
changes.

Raw room words remain authoritative.  No function here silently repairs or
normalises original data.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from typing import Iterable

from cybernoid_semantics import (
    CRP_MARKERS,
    GENERIC_CONTROLLER_CAPACITY,
    RNET_MARKERS,
    uses_generic_controller,
)

ROOM_W = 20
ROOM_H = 11

RNET_NAMES = {
    0x1F0: "RNET LEFT",
    0x1F1: "RNET RIGHT",
    0x1F4: "RNET UP",
    0x1F5: "RNET DOWN",
}
CRP_NAMES = {
    0x1FC: "CRP LEFT SLOW",
    0x1FD: "CRP LEFT FAST",
    0x1FE: "CRP RIGHT SLOW",
    0x1FF: "CRP RIGHT FAST",
}

# Each current animation family consumes one generic-controller record per source
# cell.  $24D is the exception: it owns the adjacent $24E and animates both cells.
ANIMATED_SINGLE_FAMILIES = (
    ("solid_animation_253_256", 0x253, 0x256, "descending", "solid"),
    ("energy_field_257_25A", 0x257, 0x25A, "ascending", "passable_l1_l3_lethal_l4"),
    ("energy_field_25B_25E", 0x25B, 0x25E, "ascending", "passable_l1_l3_lethal_l4"),
    ("solid_animation_25F_262", 0x25F, 0x262, "ascending", "solid"),
    ("solid_animation_263_266", 0x263, 0x266, "ascending", "solid"),
    ("solid_animation_267_26A", 0x267, 0x26A, "ascending", "solid"),
    ("solid_animation_26B_26E", 0x26B, 0x26E, "ascending", "solid"),
)

# Owned cells only.  $30C's (+2,+1) neighbour is deliberately absent: runtime
# destruction touches that context cell but it is not part of the identifying
# cannon template and varies in the original maps.
COMPOUND_TEMPLATES = {
    "compound_232_2x3": {
        "anchor": 0x232,
        "cells": ((0, 0, (0x232,)), (1, 0, (0x233,)),
                  (0, 1, (0x234,)), (1, 1, (0x235,)),
                  (0, 2, (0x236,)), (1, 2, (0x237,))),
        "controller_cost": 1,
        "edit_policy": "atomic_place_move_delete",
    },
    "compound_242_2x2": {
        "anchor": 0x242,
        "cells": ((0, 0, (0x242,)), (1, 0, (0x243,)),
                  (0, 1, (0x244,)), (1, 1, (0x245,))),
        "controller_cost": 1,
        "edit_policy": "atomic_place_move_delete",
    },
    "organic_cannon_300": {
        "anchor": 0x300,
        "cells": ((0, 0, (0x300,)),
                  (0, 1, (0x066,)),
                  (-1, 2, (0x062,)), (0, 2, (0x064,)),
                  (1, 2, (0x063,)), (2, 2, (0x065,)),
                  (-1, 3, (0x05C,)), (0, 3, (0x05D,)),
                  (1, 3, (0x05E,)), (2, 3, (0x05F, 0x210))),
        "controller_cost": 1,
        "edit_policy": "atomic_place_move_delete",
    },
    "large_cannon_30C": {
        "anchor": 0x30C,
        "cells": ((-1, -1, (0x116,)), (0, -1, (0x117,)),
                  (1, -1, (0x118,)), (2, -1, (0x119,)),
                  (-1, 0, (0x11A,)), (0, 0, (0x30C,)),
                  (1, 0, (0x30D,)), (2, 0, (0x11D,)),
                  (-1, 1, (0x11E,)), (0, 1, (0x30E,)),
                  (1, 1, (0x30F,))),
        "collateral_context": ((2, 1),),
        "controller_cost": 1,
        "edit_policy": "atomic_place_move_delete_preserve_collateral",
    },
}

# Fixed-count/synchronised structures are intentionally not represented as arbitrary
# Add/Delete operations in the safe editor.
FIXED_ENTITY_RULES = {
    "portal": {
        "count": 8,
        "level": 4,
        "edit_policy": "move_and_retarget_only",
        "sync": "marker $1D5 <-> 12-byte portal record",
    },
    "player_start": {
        "count_per_level": 1,
        "edit_policy": "move_only",
        "sync": "$02B marker <-> start-room table",
    },
    "landing_pad": {
        "count_per_level": 1,
        "edit_policy": "move_pair_only",
        "sync": "adjacent $324/$325 pair",
    },
}


@dataclass(frozen=True)
class Entity:
    kind: str
    x: int
    y: int
    cells: tuple[tuple[int, int, int], ...]
    controller_cost: int = 0
    edit_policy: str = "inspect_only"
    detail: str = ""
    runtime_role: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["cells"] = [list(cell) for cell in self.cells]
        return data


def iter_cells(room: dict):
    for y, row in enumerate(room["rows"]):
        for x, value in enumerate(row):
            yield x, y, int(value)


def value_at(room: dict, x: int, y: int) -> int | None:
    if not (0 <= x < ROOM_W and 0 <= y < ROOM_H):
        return None
    return int(room["rows"][y][x])


def generic_controller_usage(room: dict) -> dict:
    breakdown: Counter[str] = Counter()
    used = 0
    for _, _, value in iter_cells(room):
        if not uses_generic_controller(value):
            continue
        used += 1
        breakdown[generic_controller_family(value)] += 1
    return {
        "used": used,
        "capacity": GENERIC_CONTROLLER_CAPACITY,
        "free": GENERIC_CONTROLLER_CAPACITY - used,
        "breakdown": dict(sorted(breakdown.items())),
    }


def generic_controller_family(value: int) -> str:
    if value == 0x09F: return "particle_emitter"
    if value == 0x1D5: return "portal"
    if value in (0x1E0, 0x1E1): return "reactor_animation"
    if value in (0x200, 0x2E2, 0x2E6, 0x2EE): return "mixed_spawn_pit"
    if value == 0x232: return "compound_232_2x3"
    if value == 0x242: return "compound_242_2x2"
    if value == 0x24D: return "animated_pair_24D_24E"
    for name, lo, hi, _, _ in ANIMATED_SINGLE_FAMILIES:
        if lo <= value <= hi:
            return name
    if value == 0x300: return "organic_cannon_300"
    if value == 0x30C: return "large_cannon_30C"
    if value == 0x31C: return "fixed_cannon_31C"
    if value == 0x329: return "right_gun_329"
    if value == 0x346: return "left_gun_346"
    return f"controller_${value:03X}"


def _ordered_markers(room: dict, values: Iterable[int]) -> list[tuple[int, int, int]]:
    wanted = set(values)
    return [(x, y, v) for x, y, v in iter_cells(room) if v in wanted]


def rnet_load_roles(room: dict) -> list[dict]:
    """Return row-major source-marker roles at room load.

    Slots 34..41 are filled in room scan order.  Allocation failure is checked, so
    markers after the eighth do not create a live primary on that room load.
    """
    result = []
    for index, (x, y, value) in enumerate(_ordered_markers(room, RNET_MARKERS)):
        result.append({
            "x": x, "y": y, "word": value,
            "name": RNET_NAMES[value],
            "scan_index": index,
            "runtime_role": "live_primary" if index < 8 else "skipped_pool_full",
            "primary_slot": 34 + index if index < 8 else None,
        })
    return result


def crp_load_roles(room: dict) -> list[dict]:
    """Return the exact original CRP overflow behaviour in row-major scan order.

    The first six markers occupy slots 70..75.  On failure the allocator returns the
    record immediately after the range (slot 76), and the CRP caller ignores failure.
    Thus every excess source marker rewrites slot 76; after room build, only the last
    excess source remains represented there.
    """
    markers = _ordered_markers(room, CRP_MARKERS)
    result = []
    for index, (x, y, value) in enumerate(markers):
        if index < 6:
            role = "dedicated_live"
            slot = 70 + index
        elif index == len(markers) - 1:
            role = "overflow_slot76_live"
            slot = 76
        else:
            role = "overflow_overwritten"
            slot = None
        result.append({
            "x": x, "y": y, "word": value,
            "name": CRP_NAMES[value],
            "scan_index": index,
            "runtime_role": role,
            "runtime_slot": slot,
        })
    return result


def _horizontal_ele(room: dict) -> list[Entity]:
    starts = [(x, y) for x, y, v in iter_cells(room) if v == 0x1F6]
    ends = {(x, y) for x, y, v in iter_cells(room) if v == 0x1F7}
    entities = []
    used: set[tuple[int, int]] = set()
    for sx, sy in starts:
        candidates = sorted((ex, ey) for ex, ey in ends - used if ey == sy and ex > sx)
        if not candidates:
            continue
        ex, ey = candidates[0]
        used.add((ex, ey))
        entities.append(Entity(
            "ele_horizontal", sx, sy,
            ((sx, sy, 0x1F6), (ex, ey, 0x1F7)),
            controller_cost=0,
            edit_policy="atomic_place_move_delete_max_5_pairs",
            detail="two adjacent runtime object records from slots 43..52",
        ))
    return entities


def _vertical_ele(room: dict) -> list[Entity]:
    starts = [(x, y) for x, y, v in iter_cells(room) if v == 0x1F8]
    ends = {(x, y) for x, y, v in iter_cells(room) if v == 0x1F9}
    entities = []
    used: set[tuple[int, int]] = set()
    for sx, sy in starts:
        candidates = sorted((ex, ey) for ex, ey in ends - used if ex == sx and ey > sy)
        if not candidates:
            continue
        ex, ey = candidates[0]
        used.add((ex, ey))
        entities.append(Entity(
            "ele_vertical", sx, sy,
            ((sx, sy, 0x1F8), (ex, ey, 0x1F9)),
            controller_cost=0,
            edit_policy="atomic_place_move_delete_max_5_pairs",
            detail="two adjacent runtime object records from slots 43..52",
        ))
    return entities


def _compound_entity(room: dict, kind: str, x: int, y: int) -> Entity:
    spec = COMPOUND_TEMPLATES[kind]
    cells = []
    for dx, dy, allowed in spec["cells"]:
        got = value_at(room, x + dx, y + dy)
        if got is not None:
            cells.append((x + dx, y + dy, got))
    return Entity(kind, x, y, tuple(cells), spec["controller_cost"], spec["edit_policy"])


def detect_room_entities(room: dict, level_no: int) -> list[Entity]:
    """Derive high-level entities without changing raw words."""
    entities: list[Entity] = []

    for x, y, value in iter_cells(room):
        # Compound anchors own multiple source cells.
        matched = False
        for kind, spec in COMPOUND_TEMPLATES.items():
            if value == spec["anchor"]:
                entities.append(_compound_entity(room, kind, x, y))
                matched = True
                break
        if matched:
            continue

        if value == 0x24D:
            right = value_at(room, x + 1, y)
            cells = ((x, y, value),)
            if right is not None:
                cells += ((x + 1, y, right),)
            entities.append(Entity(
                "animated_pair_24D_24E", x, y, cells, 1,
                "atomic_place_move_delete",
                "5-frame horizontal pair: 24D/24E, 24F/250, 251/252, 24F/250, 24D/24E",
            ))
            continue

        for name, lo, hi, direction, collision in ANIMATED_SINGLE_FAMILIES:
            if lo <= value <= hi:
                entities.append(Entity(
                    name, x, y, ((x, y, value),), 1,
                    "single_cell_place_move_delete",
                    f"4-frame {direction} cycle ${lo:03X}-${hi:03X}; collision={collision}; source phase=${value:03X}",
                ))
                matched = True
                break
        if matched:
            continue

        if value in (0x1E0, 0x1E1):
            frames = "$308-$30B" if value == 0x1E0 else "$304-$307"
            entities.append(Entity("reactor_animation", x, y, ((x, y, value),), 1,
                                   "single_cell_place_move_delete",
                                   f"RACT {'DOWN' if value == 0x1E0 else 'UP'}; runtime frames {frames}"))
        elif value == 0x09F:
            entities.append(Entity("particle_emitter", x, y, ((x, y, value),), 1,
                                   "single_cell_place_move_delete_with_runtime_pool_warning",
                                   "child allocator uses shared slots 19..40 and checks failure"))
        elif value in (0x200, 0x2E2, 0x2E6, 0x2EE):
            entities.append(Entity("mixed_spawn_pit", x, y, ((x, y, value),), 1,
                                   "single_cell_place_move_delete_level4",
                                   "cargo or homing-hostile output; child allocations check failure"))
        elif value == 0x31C:
            entities.append(Entity("fixed_cannon_31C", x, y, ((x, y, value),), 1,
                                   "single_cell_place_move_delete"))
        elif value == 0x329:
            entities.append(Entity("right_gun_329", x, y, ((x, y, value),), 1,
                                   "single_cell_place_move_delete"))
        elif value == 0x346:
            entities.append(Entity("left_gun_346", x, y, ((x, y, value),), 1,
                                   "single_cell_place_move_delete"))
        elif value == 0x02B:
            entities.append(Entity("player_start", x, y, ((x, y, value),), 0,
                                   "move_only_sync_start_room_table"))
        elif value in (0x324, 0x325):
            # Emit only from left-half anchor.
            if value == 0x324 and value_at(room, x + 1, y) == 0x325:
                entities.append(Entity("landing_pad", x, y,
                                       ((x, y, 0x324), (x + 1, y, 0x325)), 0,
                                       "move_pair_only_one_per_level"))

    entities.extend(_horizontal_ele(room))
    entities.extend(_vertical_ele(room))

    for rec in rnet_load_roles(room):
        entities.append(Entity("rnet_source", rec["x"], rec["y"],
                               ((rec["x"], rec["y"], rec["word"]),), 0,
                               "move_delete_add_only_when_total_le_8",
                               rec["name"], rec["runtime_role"]))
    for rec in crp_load_roles(room):
        entities.append(Entity("crp_source", rec["x"], rec["y"],
                               ((rec["x"], rec["y"], rec["word"]),), 0,
                               "move_delete_add_only_when_total_le_6",
                               rec["name"], rec["runtime_role"]))

    # ST/ED forms one side-band configuration per room, but original endpoint
    # inheritance means it is intentionally advanced/move-only rather than normalised.
    side_defs = {
        "bottom": {0x1E2, 0x1E3}, "left": {0x1E4, 0x1E5},
        "top": {0x1E6, 0x1E7}, "right": {0x1E8, 0x1E9},
    }
    for side, values in side_defs.items():
        cells = tuple((x, y, v) for x, y, v in iter_cells(room) if v in values)
        if cells:
            entities.append(Entity("edge_spawn_band", cells[0][0], cells[0][1], cells, 0,
                                   "advanced_move_only_preserve_raw_cardinality",
                                   f"{side} side; persistent ST/ED endpoint semantics"))

    return entities


def portal_entities(model: dict) -> list[dict]:
    """Return the eight fixed portal entities paired by exact room/trigger tile.

    Multiple portals in one source room are valid if trigger coordinates differ.
    """
    level4 = next(level for level in model["levels"] if int(level["level"]) == 4)
    rooms = {int(room["physical_id"]): room for room in level4["rooms"]}
    markers = Counter()
    for room_no, room in rooms.items():
        for x, y, value in iter_cells(room):
            if value == 0x1D5:
                markers[(room_no, x, y)] += 1

    result = []
    for record in model["fixed_blocks"]["portal_table"]["records"]:
        sx_raw = int(record["trigger_x"])
        sy_raw = int(record["trigger_y"])
        dx_raw = int(record["destination_x"])
        dy_raw = int(record["destination_y"])
        sx = (sx_raw - 32) // 16 if (sx_raw - 32) % 16 == 0 else None
        sy = (sy_raw - 24) // 16 if (sy_raw - 24) % 16 == 0 else None
        dx = (dx_raw - 32) // 16 if (dx_raw - 32) % 16 == 0 else None
        dy = (dy_raw - 24) // 16 if (dy_raw - 24) % 16 == 0 else None
        key = (int(record["source_room"]), sx, sy) if sx is not None and sy is not None else None
        result.append({
            "index": int(record["index"]),
            "source_room": int(record["source_room"]),
            "source_tile_x": sx,
            "source_tile_y": sy,
            "source_marker_matches": bool(key is not None and markers[key] == 1),
            "destination_room": int(record["destination_room"]),
            "destination_tile_x": dx,
            "destination_tile_y": dy,
            "same_room": int(record["source_room"]) == int(record["destination_room"]),
            "edit_policy": "move_source_and_retarget_destination_fixed_count_8",
        })
    return result


def entity_catalog_rows() -> list[dict]:
    rows = []
    for kind, spec in COMPOUND_TEMPLATES.items():
        rows.append({"kind": kind, "shape": f"{len(spec['cells'])} owned cells", "controller_cost": 1,
                     "safe_add": "yes", "safe_delete": "yes", "notes": spec["edit_policy"]})
    rows.extend([
        {"kind": "animated_pair_24D_24E", "shape": "2x1 horizontal", "controller_cost": 1,
         "safe_add": "yes", "safe_delete": "yes", "notes": "five-frame two-cell animation"},
        {"kind": "animated single-cell families $253-$26E", "shape": "1 cell", "controller_cost": 1,
         "safe_add": "yes", "safe_delete": "yes", "notes": "preserve initial phase; energy fields $257-$25E are lethal only in L4"},
        {"kind": "RACT $1E0/$1E1", "shape": "1 cell", "controller_cost": 1,
         "safe_add": "yes", "safe_delete": "yes", "notes": "runtime animation $308-$30B or $304-$307"},
        {"kind": "ELE pair", "shape": "2 endpoint markers", "controller_cost": 0,
         "safe_add": "yes up to 5 pairs", "safe_delete": "yes", "notes": "two runtime slots per pair, 43..52"},
        {"kind": "portal", "shape": "$1D5 + table record", "controller_cost": 1,
         "safe_add": "no", "safe_delete": "no", "notes": "exactly 8 records; move/re-target; duplicate source rooms allowed"},
        {"kind": "RNET", "shape": "1 source marker", "controller_cost": 0,
         "safe_add": "only if room total <= 8", "safe_delete": "yes", "notes": "first eight row-major markers instantiate"},
        {"kind": "CRP", "shape": "1 source marker", "controller_cost": 0,
         "safe_add": "only if room total <= 6", "safe_delete": "yes", "notes": "original over-cap rooms preserved; excess markers overwrite slot 76"},
        {"kind": "particle emitter $09F", "shape": "1 cell", "controller_cost": 1,
         "safe_add": "yes with warning", "safe_delete": "yes", "notes": "shared child pool 19..40; allocation failure checked"},
        {"kind": "mixed spawn pit $200/$2E2", "shape": "1 cell", "controller_cost": 1,
         "safe_add": "yes in L4", "safe_delete": "yes", "notes": "$2E6/$2EE are engine aliases unused in current maps"},
        {"kind": "single-cell cannons $31C/$329/$346", "shape": "1 cell", "controller_cost": 1,
         "safe_add": "yes", "safe_delete": "yes", "notes": "projectile allocation paths guard exhaustion"},
        {"kind": "START", "shape": "1 marker + table entry", "controller_cost": 0,
         "safe_add": "no", "safe_delete": "no", "notes": "move one-per-level and synchronise start-room table"},
        {"kind": "landing pad", "shape": "2x1 $324/$325", "controller_cost": 0,
         "safe_add": "no", "safe_delete": "no", "notes": "move one pair per level"},
        {"kind": "ST/ED edge spawn", "shape": "side marker set", "controller_cost": 0,
         "safe_add": "advanced only", "safe_delete": "advanced only", "notes": "do not normalise inherited endpoints"},
    ])
    return rows
