#!/usr/bin/env python3
"""Audit an extracted Cybernoid Amiga project and decode enemy scripts.

Usage:
    python tools/cybernoid_audit.py build/project
    python tools/cybernoid_audit.py build/project \
        --json outputs/cybernoid_structural_audit.json \
        --scripts-csv outputs/cybernoid_enemy_scripts_decoded.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cybernoid_semantics import (
    audit_project,
    load_project,
    write_audit_json,
    write_enemy_script_csv,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="extracted project directory containing project.json")
    parser.add_argument("--json", type=Path, help="optional machine-readable audit output")
    parser.add_argument("--scripts-csv", type=Path, help="optional decoded enemy-script CSV")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    model = load_project(args.project)
    summary, issues = audit_project(model)

    print("Cybernoid project audit")
    print("-----------------------")
    for key, value in summary.items():
        print(f"{key}: {value}")

    if issues:
        print("\nFindings:")
        for issue in issues:
            where = []
            if issue.level is not None:
                where.append(f"L{issue.level}")
            if issue.logical_room is not None:
                where.append(f"R{issue.logical_room}")
            if issue.x is not None and issue.y is not None:
                where.append(f"({issue.x},{issue.y})")
            location = " ".join(where)
            prefix = f"[{issue.severity.upper()}] {issue.code}"
            if location:
                prefix += f" {location}"
            print(f"{prefix}: {issue.message}")

    if args.json:
        write_audit_json(summary, issues, args.json)
        print(f"\nWrote {args.json}")
    if args.scripts_csv:
        write_enemy_script_csv(model, args.scripts_csv)
        print(f"Wrote {args.scripts_csv}")

    if summary["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
