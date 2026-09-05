#!/usr/bin/env python3
"""Transactional high-level edit operations for Cybernoid room entities.

These operations mutate an extracted project model only after all structural/capacity
checks for the requested operation pass. Raw words remain the authoritative storage.
The default vacated-cell value is tile $000, which is a real blank/passable tile in
the game's passability table; callers may supply a different replacement tile.

This module deliberately does not expose ST/ED normalisation, script relocation,
portal record growth, or other operations whose runtime invariants are not fixed-size
and proven.
"""
from __future__ import annotations

from typing import Iterable

from cybernoid_entities import (
    ANIMATED_SINGLE_FAMILIES,
    COMPOUND_TEMPLATES,
    crp_load_roles,
    generic_controller_usage,
    rnet_load_roles,
)

ROOM_W = 20
ROOM_H = 11
CLEAR_TILE = 0x000
RNET_VALUES = {0x1F0, 0x1F1, 0x1F4, 0x1F5}
CRP_VALUES = {0x1FC, 0x1FD, 0x1FE, 0x1FF}
SINGLE_CONTROLLER_VALUES = {0x09F, 0x1E0, 0x1E1, 0x200, 0x2E2, 0x31C, 0x329, 0x346}
ENGINE_ALIAS_PITS = {0x2E6, 0x2EE}


class EntityEditError(ValueError):
    pass


def _levels(model: dict) -> dict[int, dict]:
    return {int(level["level"]): level for level in model["levels"]}


def _level(model: dict, level_no: int) -> dict:
    try:
        return _levels(model)[level_no]
    except KeyError as exc:
        raise EntityEditError(f"level {level_no} is not present") from exc


def _rooms(level: dict) -> dict[int, dict]:
    return {int(room["physical_id"]): room for room in level["rooms"]}


def _active_slot(level: dict, logical_room: int) -> dict:
    for slot in level["logical_slots"]:
        if int(slot["logical_id"]) == logical_room and slot.get("active"):
            return slot
    raise EntityEditError(f"logical room {logical_room} is not active in level {level['level']}")


def room_for_logical(model: dict, level_no: int, logical_room: int) -> dict:
    level = _level(model, level_no)
    slot = _active_slot(level, logical_room)
    physical = int(slot["physical_id"])
    try:
        return _rooms(level)[physical]
    except KeyError as exc:
        raise EntityEditError(
            f"logical room {logical_room} maps to missing physical room {physical}"
        ) from exc


def room_for_physical(model: dict, level_no: int, physical_room: int) -> dict:
    try:
        return _rooms(_level(model, level_no))[physical_room]
    except KeyError as exc:
        raise EntityEditError(f"physical room {physical_room} is not present in level {level_no}") from exc


def _xy(x: int, y: int) -> None:
    if not (0 <= x < ROOM_W and 0 <= y < ROOM_H):
        raise EntityEditError(f"cell ({x},{y}) is outside the 20x11 room")


def _get(room: dict, x: int, y: int) -> int:
    _xy(x, y)
    return int(room["rows"][y][x])


def _set(room: dict, x: int, y: int, value: int) -> None:
    _xy(x, y)
    room["rows"][y][x] = int(value) & 0xFFFF


def _ensure_cells_available(room: dict, cells: Iterable[tuple[int, int]], *,
                            allowed_existing: set[tuple[int, int]] | None = None,
                            allow_overwrite: bool = False) -> None:
    allowed_existing = allowed_existing or set()
    for x, y in cells:
        _xy(x, y)
        if (x, y) in allowed_existing:
            continue
        value = _get(room, x, y)
        if value != CLEAR_TILE and not allow_overwrite:
            raise EntityEditError(
                f"destination cell ({x},{y}) contains ${value:03X}; explicit overwrite required"
            )


def _controller_capacity_for_add(room: dict, cost: int = 1) -> None:
    usage = generic_controller_usage(room)
    if usage["used"] + cost > usage["capacity"]:
        raise EntityEditError(
            f"generic controller pool would exceed {usage['capacity']} "
            f"({usage['used']} used + {cost} requested)"
        )


def _tile_centre(x: int, y: int) -> tuple[int, int]:
    _xy(x, y)
    return x * 16 + 32, y * 16 + 24


def _tile_from_centre(px: int, py: int) -> tuple[int, int]:
    if (px - 32) % 16 or (py - 24) % 16:
        raise EntityEditError(f"pixel coordinate (${px:X},${py:X}) is not tile-centre aligned")
    x, y = (px - 32) // 16, (py - 24) // 16
    _xy(x, y)
    return x, y


def move_portal(model: dict, index: int, *, source_room: int, source_x: int, source_y: int,
                destination_room: int, destination_x: int, destination_y: int,
                clear_tile: int = CLEAR_TILE, allow_overwrite: bool = False) -> dict:
    """Move/re-target one of the eight fixed Level-4 portals.

    Source and destination rooms are Level-4 logical/physical IDs (0..79). The source
    marker and table record are updated atomically. Multiple portals may share a source
    room if their trigger cells differ.
    """
    if not (0 <= index < 8):
        raise EntityEditError("portal index must be 0..7")
    if not (0 <= source_room < 80 and 0 <= destination_room < 80):
        raise EntityEditError("Level-4 portal rooms must be 0..79")
    _xy(source_x, source_y); _xy(destination_x, destination_y)

    records = model["fixed_blocks"]["portal_table"]["records"]
    if len(records) != 8:
        raise EntityEditError("fixed-size editor requires exactly eight portal records")
    record = next((r for r in records if int(r["index"]) == index), None)
    if record is None:
        raise EntityEditError(f"portal record {index} is missing")

    old_room_no = int(record["source_room"])
    old_x, old_y = _tile_from_centre(int(record["trigger_x"]), int(record["trigger_y"]))
    old_room = room_for_physical(model, 4, old_room_no)
    if _get(old_room, old_x, old_y) != 0x1D5:
        raise EntityEditError(
            f"portal {index} table points to ({old_room_no},{old_x},{old_y}) without $1D5 marker"
        )

    new_room = room_for_physical(model, 4, source_room)
    same_cell = old_room_no == source_room and old_x == source_x and old_y == source_y
    if not same_cell:
        _ensure_cells_available(new_room, [(source_x, source_y)], allow_overwrite=allow_overwrite)
        if old_room_no != source_room:
            _controller_capacity_for_add(new_room, 1)

    # Reject exact duplicate trigger records: runtime table order would make later one unreachable.
    new_px, new_py = _tile_centre(source_x, source_y)
    for other in records:
        if int(other["index"]) == index:
            continue
        if (int(other["source_room"]) == source_room and
                int(other["trigger_x"]) == new_px and int(other["trigger_y"]) == new_py):
            raise EntityEditError("another portal record already uses that source trigger")

    if not same_cell:
        _set(old_room, old_x, old_y, clear_tile)
        _set(new_room, source_x, source_y, 0x1D5)

    dest_px, dest_py = _tile_centre(destination_x, destination_y)
    record.update({
        "source_room": source_room,
        "trigger_x": new_px,
        "trigger_y": new_py,
        "destination_room": destination_room,
        "destination_x": dest_px,
        "destination_y": dest_py,
    })
    return {
        "operation": "move_portal", "index": index,
        "old_source": (old_room_no, old_x, old_y),
        "new_source": (source_room, source_x, source_y),
        "destination": (destination_room, destination_x, destination_y),
    }


def move_start(model: dict, level_no: int, *, logical_room: int, x: int, y: int,
               clear_tile: int = CLEAR_TILE, allow_overwrite: bool = False) -> dict:
    """Move the one START marker for a level and synchronise the start-room table."""
    _xy(x, y)
    level = _level(model, level_no)
    found = []
    for room in level["rooms"]:
        p = int(room["physical_id"])
        for yy, row in enumerate(room["rows"]):
            for xx, value in enumerate(row):
                if int(value) == 0x02B:
                    found.append((room, p, xx, yy))
    if len(found) != 1:
        raise EntityEditError(f"level {level_no} has {len(found)} START markers; expected one")

    target = room_for_logical(model, level_no, logical_room)
    old_room, old_p, old_x, old_y = found[0]
    target_p = int(target["physical_id"])
    same_cell = old_p == target_p and old_x == x and old_y == y
    if not same_cell:
        _ensure_cells_available(target, [(x, y)], allow_overwrite=allow_overwrite)
        _set(old_room, old_x, old_y, clear_tile)
        _set(target, x, y, 0x02B)

    model["fixed_blocks"]["start_rooms"][level_no - 1] = logical_room
    return {
        "operation": "move_start", "level": level_no,
        "old": (old_p, old_x, old_y),
        "new": (logical_room, target_p, x, y),
    }


def move_landing_pad(model: dict, level_no: int, *, logical_room: int, x: int, y: int,
                     clear_tile: int = CLEAR_TILE, allow_overwrite: bool = False) -> dict:
    """Move the one adjacent $324/$325 level-end landing pair."""
    if x >= ROOM_W - 1:
        raise EntityEditError("landing pad requires two horizontal cells")
    _xy(x, y)
    level = _level(model, level_no)
    pairs = []
    for room in level["rooms"]:
        p = int(room["physical_id"])
        for yy in range(ROOM_H):
            for xx in range(ROOM_W - 1):
                if _get(room, xx, yy) == 0x324 and _get(room, xx + 1, yy) == 0x325:
                    pairs.append((room, p, xx, yy))
    if len(pairs) != 1:
        raise EntityEditError(f"level {level_no} has {len(pairs)} landing-pad pairs; expected one")

    target = room_for_logical(model, level_no, logical_room)
    old_room, old_p, old_x, old_y = pairs[0]
    target_p = int(target["physical_id"])
    same = old_p == target_p and old_x == x and old_y == y
    if not same:
        old_cells = {(old_x, old_y), (old_x + 1, old_y)} if old_p == target_p else set()
        _ensure_cells_available(target, [(x, y), (x + 1, y)],
                                allowed_existing=old_cells, allow_overwrite=allow_overwrite)
        _set(old_room, old_x, old_y, clear_tile); _set(old_room, old_x + 1, old_y, clear_tile)
        _set(target, x, y, 0x324); _set(target, x + 1, y, 0x325)
    return {"operation": "move_landing_pad", "level": level_no,
            "old": (old_p, old_x, old_y), "new": (logical_room, target_p, x, y)}


def _ele_pairs(room: dict) -> list[tuple[str, int, int, int, int]]:
    pairs = []
    # Canonical one-to-one nearest endpoint matching, same as structural audit.
    h_ends = {(x, y) for y in range(ROOM_H) for x in range(ROOM_W) if _get(room, x, y) == 0x1F7}
    used_h = set()
    for y in range(ROOM_H):
        for x in range(ROOM_W):
            if _get(room, x, y) != 0x1F6:
                continue
            cand = sorted((ex, ey) for ex, ey in h_ends - used_h if ey == y and ex > x)
            if cand:
                ex, ey = cand[0]; used_h.add((ex, ey)); pairs.append(("horizontal", x, y, ex, ey))
    v_ends = {(x, y) for y in range(ROOM_H) for x in range(ROOM_W) if _get(room, x, y) == 0x1F9}
    used_v = set()
    for y in range(ROOM_H):
        for x in range(ROOM_W):
            if _get(room, x, y) != 0x1F8:
                continue
            cand = sorted((ex, ey) for ex, ey in v_ends - used_v if ex == x and ey > y)
            if cand:
                ex, ey = cand[0]; used_v.add((ex, ey)); pairs.append(("vertical", x, y, ex, ey))
    return pairs


def add_ele_pair(room: dict, orientation: str, *, start_x: int, start_y: int,
                 end_x: int, end_y: int, allow_overwrite: bool = False) -> dict:
    pairs = _ele_pairs(room)
    if len(pairs) >= 5:
        raise EntityEditError("ELE runtime slots 43..52 allow at most five pairs per room")
    _xy(start_x, start_y); _xy(end_x, end_y)
    if orientation == "horizontal":
        if start_y != end_y or not (end_x > start_x):
            raise EntityEditError("horizontal ELE end must be to the right on the same row")
        start_word, end_word = 0x1F6, 0x1F7
    elif orientation == "vertical":
        if start_x != end_x or not (end_y > start_y):
            raise EntityEditError("vertical ELE end must be below in the same column")
        start_word, end_word = 0x1F8, 0x1F9
    else:
        raise EntityEditError("orientation must be horizontal or vertical")
    _ensure_cells_available(room, [(start_x, start_y), (end_x, end_y)],
                            allow_overwrite=allow_overwrite)
    _set(room, start_x, start_y, start_word); _set(room, end_x, end_y, end_word)
    return {"operation": "add_ele_pair", "orientation": orientation,
            "start": (start_x, start_y), "end": (end_x, end_y)}


def delete_ele_pair(room: dict, orientation: str, *, start_x: int, start_y: int,
                    clear_tile: int = CLEAR_TILE) -> dict:
    pair = next((p for p in _ele_pairs(room)
                 if p[0] == orientation and p[1] == start_x and p[2] == start_y), None)
    if pair is None:
        raise EntityEditError("matching ELE pair not found")
    _, sx, sy, ex, ey = pair
    _set(room, sx, sy, clear_tile); _set(room, ex, ey, clear_tile)
    return {"operation": "delete_ele_pair", "orientation": orientation,
            "start": (sx, sy), "end": (ex, ey)}


def move_ele_pair(room: dict, orientation: str, *, old_start_x: int, old_start_y: int,
                  new_start_x: int, new_start_y: int, new_end_x: int, new_end_y: int,
                  clear_tile: int = CLEAR_TILE, allow_overwrite: bool = False) -> dict:
    pair = next((p for p in _ele_pairs(room)
                 if p[0] == orientation and p[1] == old_start_x and p[2] == old_start_y), None)
    if pair is None:
        raise EntityEditError("matching ELE pair not found")
    _, sx, sy, ex, ey = pair
    old_cells = {(sx, sy), (ex, ey)}
    if orientation == "horizontal":
        if new_start_y != new_end_y or not (new_end_x > new_start_x):
            raise EntityEditError("horizontal ELE end must be right of start on same row")
        sw, ew = 0x1F6, 0x1F7
    elif orientation == "vertical":
        if new_start_x != new_end_x or not (new_end_y > new_start_y):
            raise EntityEditError("vertical ELE end must be below start in same column")
        sw, ew = 0x1F8, 0x1F9
    else:
        raise EntityEditError("orientation must be horizontal or vertical")
    _ensure_cells_available(room, [(new_start_x, new_start_y), (new_end_x, new_end_y)],
                            allowed_existing=old_cells, allow_overwrite=allow_overwrite)
    for ox, oy in old_cells:
        _set(room, ox, oy, clear_tile)
    _set(room, new_start_x, new_start_y, sw); _set(room, new_end_x, new_end_y, ew)
    return {"operation": "move_ele_pair", "orientation": orientation,
            "old": ((sx, sy), (ex, ey)), "new": ((new_start_x, new_start_y), (new_end_x, new_end_y))}


def _template_instance(room: dict, kind: str, x: int, y: int) -> list[tuple[int, int, int]]:
    try:
        spec = COMPOUND_TEMPLATES[kind]
    except KeyError as exc:
        raise EntityEditError(f"unknown compound kind {kind}") from exc
    cells = []
    for dx, dy, allowed in spec["cells"]:
        xx, yy = x + dx, y + dy
        _xy(xx, yy)
        got = _get(room, xx, yy)
        if got not in allowed:
            allowed_text = "/".join(f"${v:03X}" for v in allowed)
            raise EntityEditError(
                f"{kind} at ({x},{y}) invalid at ({xx},{yy}): expected {allowed_text}, got ${got:03X}"
            )
        cells.append((xx, yy, got))
    return cells


def add_compound(room: dict, kind: str, *, x: int, y: int,
                 allow_overwrite: bool = False) -> dict:
    try:
        spec = COMPOUND_TEMPLATES[kind]
    except KeyError as exc:
        raise EntityEditError(f"unknown compound kind {kind}") from exc
    _controller_capacity_for_add(room, int(spec["controller_cost"]))
    destinations = [(x + dx, y + dy) for dx, dy, _ in spec["cells"]]
    _ensure_cells_available(room, destinations, allow_overwrite=allow_overwrite)
    written = []
    for dx, dy, allowed in spec["cells"]:
        value = allowed[0]  # canonical source phase; existing variants are preserved by move.
        _set(room, x + dx, y + dy, value)
        written.append((x + dx, y + dy, value))
    return {"operation": "add_compound", "kind": kind, "anchor": (x, y), "cells": written}


def delete_compound(room: dict, kind: str, *, x: int, y: int,
                    clear_tile: int = CLEAR_TILE) -> dict:
    cells = _template_instance(room, kind, x, y)
    for xx, yy, _ in cells:
        _set(room, xx, yy, clear_tile)
    # $30C collateral/context cell (+2,+1) is deliberately untouched.
    return {"operation": "delete_compound", "kind": kind, "anchor": (x, y), "cells": cells}


def move_compound(room: dict, kind: str, *, old_x: int, old_y: int,
                  new_x: int, new_y: int, clear_tile: int = CLEAR_TILE,
                  allow_overwrite: bool = False) -> dict:
    spec = COMPOUND_TEMPLATES.get(kind)
    if spec is None:
        raise EntityEditError(f"unknown compound kind {kind}")
    old_cells = _template_instance(room, kind, old_x, old_y)
    old_positions = {(x, y) for x, y, _ in old_cells}
    offsets_and_values = []
    for dx, dy, _ in spec["cells"]:
        ox, oy = old_x + dx, old_y + dy
        offsets_and_values.append((dx, dy, _get(room, ox, oy)))
    destinations = [(new_x + dx, new_y + dy) for dx, dy, _ in spec["cells"]]
    _ensure_cells_available(room, destinations, allowed_existing=old_positions,
                            allow_overwrite=allow_overwrite)
    for ox, oy in old_positions:
        _set(room, ox, oy, clear_tile)
    for dx, dy, value in offsets_and_values:
        _set(room, new_x + dx, new_y + dy, value)
    return {"operation": "move_compound", "kind": kind,
            "old_anchor": (old_x, old_y), "new_anchor": (new_x, new_y)}


def _is_animated_single(value: int) -> bool:
    return any(lo <= value <= hi for _, lo, hi, _, _ in ANIMATED_SINGLE_FAMILIES)


def add_single_controller(room: dict, level_no: int, value: int, *, x: int, y: int,
                          allow_overwrite: bool = False) -> dict:
    if not (_is_animated_single(value) or value in SINGLE_CONTROLLER_VALUES):
        if value in ENGINE_ALIAS_PITS:
            raise EntityEditError("$2E6/$2EE are engine-supported pit aliases but intentionally hidden from normal Add")
        raise EntityEditError(f"${value:03X} is not an approved single-controller Add entity")
    if value in (0x200, 0x2E2) and level_no != 4:
        raise EntityEditError("mixed spawn pits are Level-4 entities")
    _controller_capacity_for_add(room, 1)
    _ensure_cells_available(room, [(x, y)], allow_overwrite=allow_overwrite)
    _set(room, x, y, value)
    return {"operation": "add_single_controller", "word": value, "cell": (x, y)}


def move_single_controller(room: dict, value: int, *, old_x: int, old_y: int,
                           new_x: int, new_y: int, clear_tile: int = CLEAR_TILE,
                           allow_overwrite: bool = False) -> dict:
    if _get(room, old_x, old_y) != value:
        raise EntityEditError(f"source cell does not contain ${value:03X}")
    same = old_x == new_x and old_y == new_y
    if not same:
        _ensure_cells_available(room, [(new_x, new_y)], allowed_existing={(old_x, old_y)},
                                allow_overwrite=allow_overwrite)
        _set(room, old_x, old_y, clear_tile); _set(room, new_x, new_y, value)
    return {"operation": "move_single_controller", "word": value,
            "old": (old_x, old_y), "new": (new_x, new_y)}


def delete_single_controller(room: dict, value: int, *, x: int, y: int,
                             clear_tile: int = CLEAR_TILE) -> dict:
    if _get(room, x, y) != value:
        raise EntityEditError(f"cell ({x},{y}) does not contain ${value:03X}")
    _set(room, x, y, clear_tile)
    return {"operation": "delete_single_controller", "word": value, "cell": (x, y)}


def add_animated_pair_24d(room: dict, *, x: int, y: int,
                          allow_overwrite: bool = False) -> dict:
    if x >= ROOM_W - 1:
        raise EntityEditError("$24D/$24E pair requires two horizontal cells")
    _controller_capacity_for_add(room, 1)
    _ensure_cells_available(room, [(x, y), (x + 1, y)], allow_overwrite=allow_overwrite)
    _set(room, x, y, 0x24D); _set(room, x + 1, y, 0x24E)
    return {"operation": "add_animated_pair_24d", "anchor": (x, y)}


def move_animated_pair_24d(room: dict, *, old_x: int, old_y: int,
                           new_x: int, new_y: int, clear_tile: int = CLEAR_TILE,
                           allow_overwrite: bool = False) -> dict:
    if _get(room, old_x, old_y) != 0x24D or old_x >= ROOM_W - 1 or _get(room, old_x + 1, old_y) != 0x24E:
        raise EntityEditError("source is not a canonical $24D/$24E pair")
    if new_x >= ROOM_W - 1:
        raise EntityEditError("$24D/$24E pair requires two horizontal cells")
    old_positions = {(old_x, old_y), (old_x + 1, old_y)}
    _ensure_cells_available(room, [(new_x, new_y), (new_x + 1, new_y)],
                            allowed_existing=old_positions, allow_overwrite=allow_overwrite)
    for xx, yy in old_positions: _set(room, xx, yy, clear_tile)
    _set(room, new_x, new_y, 0x24D); _set(room, new_x + 1, new_y, 0x24E)
    return {"operation": "move_animated_pair_24d", "old": (old_x, old_y), "new": (new_x, new_y)}


def delete_animated_pair_24d(room: dict, *, x: int, y: int,
                             clear_tile: int = CLEAR_TILE) -> dict:
    if _get(room, x, y) != 0x24D or x >= ROOM_W - 1 or _get(room, x + 1, y) != 0x24E:
        raise EntityEditError("source is not a canonical $24D/$24E pair")
    _set(room, x, y, clear_tile); _set(room, x + 1, y, clear_tile)
    return {"operation": "delete_animated_pair_24d", "anchor": (x, y)}


def add_rnet(room: dict, value: int, *, x: int, y: int,
             allow_overwrite: bool = False) -> dict:
    if value not in RNET_VALUES:
        raise EntityEditError("RNET value must be $1F0/$1F1/$1F4/$1F5")
    if len(rnet_load_roles(room)) >= 8:
        raise EntityEditError("safe Add RNET is limited to rooms with fewer than eight source markers")
    _ensure_cells_available(room, [(x, y)], allow_overwrite=allow_overwrite)
    _set(room, x, y, value)
    return {"operation": "add_rnet", "cell": (x, y), "word": value,
            "roles_after": rnet_load_roles(room)}


def add_crp(room: dict, value: int, *, x: int, y: int,
            allow_overwrite: bool = False) -> dict:
    if value not in CRP_VALUES:
        raise EntityEditError("CRP value must be $1FC-$1FF")
    if len(crp_load_roles(room)) >= 6:
        raise EntityEditError("safe Add CRP is limited to rooms with fewer than six source markers")
    _ensure_cells_available(room, [(x, y)], allow_overwrite=allow_overwrite)
    _set(room, x, y, value)
    return {"operation": "add_crp", "cell": (x, y), "word": value,
            "roles_after": crp_load_roles(room)}


def move_runtime_source(room: dict, value: int, *, old_x: int, old_y: int,
                        new_x: int, new_y: int, clear_tile: int = CLEAR_TILE,
                        allow_overwrite: bool = False) -> dict:
    """Move an existing RNET/CRP source, preserving even original over-cap layouts.

    Moving can change row-major allocation priority. The returned before/after role
    lists make that effect explicit to the UI rather than silently preserving a stale
    'live' label.
    """
    if value not in RNET_VALUES | CRP_VALUES:
        raise EntityEditError("runtime source must be RNET or CRP")
    if _get(room, old_x, old_y) != value:
        raise EntityEditError(f"source cell does not contain ${value:03X}")
    before = rnet_load_roles(room) if value in RNET_VALUES else crp_load_roles(room)
    if (old_x, old_y) != (new_x, new_y):
        _ensure_cells_available(room, [(new_x, new_y)], allowed_existing={(old_x, old_y)},
                                allow_overwrite=allow_overwrite)
        _set(room, old_x, old_y, clear_tile); _set(room, new_x, new_y, value)
    after = rnet_load_roles(room) if value in RNET_VALUES else crp_load_roles(room)
    return {"operation": "move_runtime_source", "word": value,
            "old": (old_x, old_y), "new": (new_x, new_y),
            "roles_before": before, "roles_after": after}


def delete_runtime_source(room: dict, value: int, *, x: int, y: int,
                          clear_tile: int = CLEAR_TILE) -> dict:
    if value not in RNET_VALUES | CRP_VALUES:
        raise EntityEditError("runtime source must be RNET or CRP")
    if _get(room, x, y) != value:
        raise EntityEditError(f"cell does not contain ${value:03X}")
    before = rnet_load_roles(room) if value in RNET_VALUES else crp_load_roles(room)
    _set(room, x, y, clear_tile)
    after = rnet_load_roles(room) if value in RNET_VALUES else crp_load_roles(room)
    return {"operation": "delete_runtime_source", "word": value, "cell": (x, y),
            "roles_before": before, "roles_after": after}
