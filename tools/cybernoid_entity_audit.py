#!/usr/bin/env python3
"""Export Cybernoid's derived high-level room entities from an extracted project."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cybernoid_entities import (
    detect_room_entities,
    entity_catalog_rows,
    generic_controller_usage,
    portal_entities,
)


def load_project(path: Path) -> dict:
    return json.loads((path / "project.json").read_text(encoding="utf-8"))


def logical_for_physical(level: dict, physical: int) -> list[int]:
    return [int(slot["logical_id"]) for slot in level["logical_slots"]
            if slot.get("active") and int(slot["physical_id"]) == physical]


def export(model: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    controller_rows = []
    kind_counts: dict[str, int] = {}

    for level in model["levels"]:
        level_no = int(level["level"])
        for room in level["rooms"]:
            physical = int(room["physical_id"])
            logical_refs = logical_for_physical(level, physical)
            usage = generic_controller_usage(room)
            controller_rows.append({
                "level": level_no,
                "physical_room": physical,
                "logical_rooms": ";".join(str(v) for v in logical_refs),
                "used": usage["used"],
                "capacity": usage["capacity"],
                "free": usage["free"],
                "breakdown_json": json.dumps(usage["breakdown"], sort_keys=True),
            })
            for entity in detect_room_entities(room, level_no):
                d = entity.to_dict()
                kind_counts[d["kind"]] = kind_counts.get(d["kind"], 0) + 1
                rows.append({
                    "level": level_no,
                    "physical_room": physical,
                    "logical_rooms": ";".join(str(v) for v in logical_refs),
                    "kind": d["kind"],
                    "anchor_x": d["x"],
                    "anchor_y": d["y"],
                    "controller_cost": d["controller_cost"],
                    "edit_policy": d["edit_policy"],
                    "runtime_role": d["runtime_role"],
                    "detail": d["detail"],
                    "cells_json": json.dumps(d["cells"]),
                })

    with (out_dir / "cybernoid_entities.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = ["level", "physical_room", "logical_rooms", "kind", "anchor_x", "anchor_y",
                  "controller_cost", "edit_policy", "runtime_role", "detail", "cells_json"]
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)

    with (out_dir / "cybernoid_controller_budget.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = ["level", "physical_room", "logical_rooms", "used", "capacity", "free", "breakdown_json"]
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(controller_rows)

    with (out_dir / "cybernoid_entity_catalog.csv").open("w", newline="", encoding="utf-8") as fh:
        catalog = entity_catalog_rows()
        fields = ["kind", "shape", "controller_cost", "safe_add", "safe_delete", "notes"]
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(catalog)

    portals = portal_entities(model)
    (out_dir / "cybernoid_portals_semantic.json").write_text(json.dumps(portals, indent=2) + "\n", encoding="utf-8")

    summary = {
        "entity_count": len(rows),
        "kind_counts": dict(sorted(kind_counts.items())),
        "max_controller_room": max(controller_rows, key=lambda r: int(r["used"])) if controller_rows else None,
        "portals": portals,
    }
    (out_dir / "cybernoid_entity_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("project", type=Path)
    p.add_argument("--out", type=Path, default=Path("outputs/entity_audit"))
    args = p.parse_args()
    summary = export(load_project(args.project), args.out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
