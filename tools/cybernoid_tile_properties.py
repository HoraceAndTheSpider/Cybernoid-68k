#!/usr/bin/env python3
"""Tile collision/destruction metadata for Cybernoid Amiga room editing.

The room loader keeps the source word in the live collision map unless the value is
listed in the 67-word passability table at runtime $113FC.  Special control markers
can have additional runtime behaviour, so the API reports both a broad editor class
and the underlying collision evidence rather than pretending every special marker is
an ordinary background tile.
"""
from __future__ import annotations

import csv
from pathlib import Path

TILE_COUNT = 961

# Verified directly from GAME runtime $113FC (67 words; $1DD/$1DE are duplicated in
# the source table, hence the set is slightly smaller).
PASSABLE_VALUES = {
    0x000, 0x001, 0x002, 0x003, 0x004, 0x005, 0x006, 0x008, 0x00A, 0x00B, 0x00E,
    0x044, 0x045, 0x046, 0x047, 0x048, 0x049, 0x04A, 0x04B, 0x04C, 0x04D, 0x04E,
    0x09A, 0x09B, 0x09C, 0x143,
    0x1D5, 0x1D6, 0x1D7, 0x1D8, 0x1D9, 0x1DA, 0x1DB, 0x1DC, 0x1DD, 0x1DE,
    0x21B,
    0x257, 0x258, 0x259, 0x25A, 0x25B, 0x25C, 0x25D, 0x25E,
    0x2D6, 0x2D7, 0x2D8, 0x2D9, 0x2DA, 0x2DB, 0x2DC, 0x2DD, 0x2DE, 0x2DF, 0x2E0, 0x2E1,
    0x116, 0x119, 0x11A, 0x11D, 0x11E, 0x30D, 0x30E, 0x30F,
}

# Tiles proved to participate in destructible source structures.  Some individual
# cells are passable while the whole multi-cell structure is destructible; both facts
# are reported by tile_info().
DESTRUCTIBLE_VALUES = {
    # single-cell destructibles
    0x068, 0x069, 0x06B, 0x0ED,
    # 2x3
    0x232, 0x233, 0x234, 0x235, 0x236, 0x237,
    # 2x2
    0x242, 0x243, 0x244, 0x245,
    # organic cannon $300 footprint
    0x300, 0x066, 0x062, 0x064, 0x063, 0x065,
    0x05C, 0x05D, 0x05E, 0x05F, 0x210,
    # large destructible cannon $30C footprint
    0x30C, 0x30D, 0x30E, 0x30F,
    0x116, 0x117, 0x118, 0x119, 0x11A, 0x11D, 0x11E,
}

ENERGY_FIELD_VALUES = set(range(0x257, 0x25F))
ANIMATED_SOLID_VALUES = set(range(0x253, 0x257)) | set(range(0x25F, 0x26F))
ANIMATED_PAIR_VALUES = set(range(0x24D, 0x253))

# Values with known non-background semantics.  The MARKERS dictionary lives in
# cybernoid_semantics, but duplicating the compact ID set here keeps this module free
# of circular imports and usable as a standalone CSV generator.
SPECIAL_CONTROL_VALUES = {
    0x02B, 0x09F, 0x1D5,
    0x1E0, 0x1E1, 0x1E2, 0x1E3, 0x1E4, 0x1E5, 0x1E6, 0x1E7, 0x1E8, 0x1E9,
    0x1F0, 0x1F1, 0x1F2, 0x1F3, 0x1F4, 0x1F5, 0x1F6, 0x1F7, 0x1F8, 0x1F9,
    0x1FA, 0x1FC, 0x1FD, 0x1FE, 0x1FF,
    0x200, 0x2E2, 0x2E6, 0x2EE,
    0x300, 0x30C, 0x31C, 0x324, 0x325, 0x329, 0x346,
} | ANIMATED_PAIR_VALUES | set(range(0x253, 0x26F))

# Runtime-owned source footprints for the cannon/gun anchors discussed by the editor.
# These are source-map requirements, not all animation frames.

ENTITY_COMPONENT_NOTES = {
    0x31D: "Required partner cell for the $31C fixed cannon.",
    0x326: "Left-most body cell of the $329 right-facing gun.",
    0x327: "Body cell of the $329 right-facing gun.",
    0x328: "Body cell immediately left of the $329 right-facing gun controller/tip.",
    0x347: "Body cell immediately right of the $346 left-facing gun controller/tip.",
    0x348: "Body cell of the $346 left-facing gun.",
    0x349: "Normal right-most body/end cell of the $346 left-facing gun.",
    0x359: "Original alternate end-cap seen on one $346 gun placement.",
}

CANNON_FOOTPRINTS = {
    0x31C: {
        "name": "$31C fixed cannon",
        "cells": ((0, 0, (0x31C,)), (1, 0, (0x31D,))),
        "notes": "two-cell source pair; runtime animates the pair",
    },
    0x329: {
        "name": "$329 right-facing gun",
        "cells": ((-3, 0, (0x326,)), (-2, 0, (0x327,)), (-1, 0, (0x328,)), (0, 0, (0x329,))),
        "notes": "four-cell source strip; all $329 guns share fire timer $3FF2C",
    },
    0x346: {
        "name": "$346 left-facing gun",
        "cells": ((0, 0, (0x346,)), (1, 0, (0x347,)), (2, 0, (0x348,)), (3, 0, (0x349, 0x359))),
        "notes": "four-cell source strip; one original instance uses $359 end-cap; all $346 guns share fire timer $3FF2A",
    },
}


def tile_info(value: int, level_no: int | None = None) -> dict:
    """Return editor-facing collision/destruction information for one room word.

    `class` is intentionally broad and visual. `collision` is the closer statement
    about movement/collision. Special controls retain a `special=True` flag even when
    their raw value also appears in the passability table.
    """
    value = int(value) & 0xFFFF
    in_bank = 0 <= value < TILE_COUNT
    passable_table = value in PASSABLE_VALUES
    destructible = value in DESTRUCTIBLE_VALUES
    special = value in SPECIAL_CONTROL_VALUES

    if value in ENERGY_FIELD_VALUES:
        if level_no == 4:
            collision = "lethal / blocking in Level 4"
            broad = "hazard"
            note = "Passability table normally clears this cell, but Level 4 replaces live collision with $1234."
        else:
            collision = "passable"
            broad = "special"
            note = "Animated energy field; passable in Levels 1-3, lethal in Level 4."
    elif special:
        # For special values, the passability-table result is still useful evidence,
        # but the special handler may create objects/state in addition to collision.
        collision = "passable" if passable_table else "special / runtime-controlled"
        broad = "destructible" if destructible else "special"
        if value in CANNON_FOOTPRINTS:
            note = CANNON_FOOTPRINTS[value]["notes"]
        else:
            note = "Special/control value; the room loader performs extra runtime handling."
    else:
        collision = "passable" if passable_table else "solid"
        broad = "destructible" if destructible else collision
        note = ENTITY_COMPONENT_NOTES.get(value, "")

    return {
        "value": value,
        "tile_id": value if in_bank else None,
        "in_tile_bank": in_bank,
        "class": broad,
        "collision": collision,
        "passable_table": passable_table,
        "destructible": destructible,
        "special": special,
        "note": note,
    }


def palette_class(value: int, level_no: int | None = None) -> str:
    """Return the single colour-key class used by the pygame palette/overlay."""
    info = tile_info(value, level_no)
    if info["class"] == "hazard":
        return "hazard"
    if info["destructible"]:
        return "destructible"
    if info["special"]:
        return "special"
    return "passable" if info["passable_table"] else "solid"


def write_tile_properties_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=(
            "tile_id", "class_l1_l3", "class_l4", "collision_l1_l3", "collision_l4",
            "passable_table", "destructible", "special", "notes",
        ))
        writer.writeheader()
        for value in range(TILE_COUNT):
            normal = tile_info(value, 1)
            l4 = tile_info(value, 4)
            notes = normal["note"] or l4["note"]
            writer.writerow({
                "tile_id": f"${value:03X}",
                "class_l1_l3": palette_class(value, 1),
                "class_l4": palette_class(value, 4),
                "collision_l1_l3": normal["collision"],
                "collision_l4": l4["collision"],
                "passable_table": "yes" if normal["passable_table"] else "no",
                "destructible": "yes" if normal["destructible"] else "no",
                "special": "yes" if normal["special"] else "no",
                "notes": notes,
            })


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Write Cybernoid tile collision/destruction metadata CSV")
    p.add_argument("output", type=Path)
    args = p.parse_args()
    write_tile_properties_csv(args.output)
